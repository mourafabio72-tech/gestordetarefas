import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from ..database import get_db
from typing import Optional
from ..models import Obrigacao, Empresa, Setor, Usuario, EmpresaObrigacaoDetalhe
from ..schemas import ObrigacaoCreate, ObrigacaoUpdate, ObrigacaoResponse
from ..auth import get_current_user, require_perm, require_flag
from ..services.gerador import gerar_tarefas, deslocamento_competencia
from ..seguranca import log_event, ip_cliente

router = APIRouter(prefix="/obrigacoes", tags=["obrigacoes"])


class DetalheItem(BaseModel):
    empresa_id: int
    observacao: Optional[str] = None


class DetalhesBody(BaseModel):
    itens: List[DetalheItem]


@router.get("/{obrigacao_id}/excecoes")
def get_excecoes(obrigacao_id: int, db: Session = Depends(get_db),
                 current_user: Usuario = Depends(require_perm("obrigacoes", "ver"))):
    """Empresas que alguém decidiu que esta obrigação NÃO alcança."""
    from ..models import ObrigacaoExcecao
    out = []
    for x in (db.query(ObrigacaoExcecao)
              .filter(ObrigacaoExcecao.obrigacao_id == obrigacao_id)
              .order_by(ObrigacaoExcecao.created_at.desc()).all()):
        out.append({"id": x.id, "empresa_id": x.empresa_id,
                    "empresa_nome": x.empresa.razao_social if x.empresa else "?",
                    "motivo": x.motivo or "",
                    "decidido_por": x.decidido_por.nome if x.decidido_por else None,
                    "created_at": x.created_at})
    return out


@router.delete("/{obrigacao_id}/excecoes/{excecao_id}")
def remover_excecao(obrigacao_id: int, excecao_id: int, request: Request,
                    db: Session = Depends(get_db),
                    current_user: Usuario = Depends(require_perm("obrigacoes", "editar"))):
    """Desfaz a exceção: a empresa volta a gerar tarefa desta obrigação.

    A volta é o que impede um clique errado de prender a empresa fora da
    obrigação para sempre. A tarefa que já foi cancelada continua cancelada:
    desfazer a regra não ressuscita o passado, e a próxima geração cria a do
    mês corrente se ela ainda não existir."""
    from ..models import ObrigacaoExcecao
    x = (db.query(ObrigacaoExcecao)
         .filter(ObrigacaoExcecao.id == excecao_id,
                 ObrigacaoExcecao.obrigacao_id == obrigacao_id).first())
    if not x:
        raise HTTPException(status_code=404, detail="Exceção não encontrada")
    empresa_id = x.empresa_id
    db.delete(x)
    db.commit()
    # Aqui a exceção é APAGADA, então o evento é o de exclusão. Saía como
    # `EDICAO_REGISTRO_CRITICO`, o irmão do nome trocado em `routes/tarefas.py`.
    log_event("EXCLUSAO_REGISTRO_CRITICO", tabela="obrigacao_excecao", acao="removida",
              obrigacao_id=obrigacao_id, empresa_id=empresa_id,
              user_id=current_user.id, ip=ip_cliente(request))
    return {"ok": True}


@router.get("/{obrigacao_id}/detalhes-empresa")
def get_detalhes_empresa(obrigacao_id: int, db: Session = Depends(get_db),
                         current_user: Usuario = Depends(get_current_user)):
    """Detalhes fixos por empresa nesta obrigação (ex.: 'Empréstimo do Banco X')."""
    out = []
    for d in db.query(EmpresaObrigacaoDetalhe).filter(EmpresaObrigacaoDetalhe.obrigacao_id == obrigacao_id).all():
        emp = db.query(Empresa).filter(Empresa.id == d.empresa_id).first()
        out.append({"empresa_id": d.empresa_id,
                    "empresa_nome": emp.razao_social if emp else "?",
                    "observacao": d.observacao or ""})
    return out


@router.put("/{obrigacao_id}/detalhes-empresa")
def set_detalhes_empresa(obrigacao_id: int, body: DetalhesBody, db: Session = Depends(get_db),
                         current_user: Usuario = Depends(require_perm("obrigacoes", "editar"))):
    """Regrava os detalhes; só mantém os que têm texto."""
    if not db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first():
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    db.query(EmpresaObrigacaoDetalhe).filter(EmpresaObrigacaoDetalhe.obrigacao_id == obrigacao_id).delete()
    gravados = 0
    for it in body.itens:
        texto = (it.observacao or "").strip()
        if texto:
            db.add(EmpresaObrigacaoDetalhe(obrigacao_id=obrigacao_id, empresa_id=it.empresa_id, observacao=texto))
            gravados += 1
    db.commit()
    # A rota irmã de responsáveis por setor (`routes/empresas.py`) já emitia
    # este evento na mesma forma, apaga e regrava. Ficar de fora aqui era
    # inconsistência, e não decisão.
    log_event("EDICAO_REGISTRO_CRITICO", tabela="empresa_obrigacao_detalhe",
              obrigacao_id=obrigacao_id, quantidade=gravados)
    return {"ok": True}

def _comp_label(ref) -> str:
    """Rótulo da competência no Excel, a mesma regra de `rotuloCompetencia`
    (`RelacaoObrigacoes.jsx`). Só os quatro apelidos tinham nome; o
    deslocamento numérico da anual (-14) saía cru na planilha."""
    if ref is None or str(ref).strip() == "":
        return ""
    n = deslocamento_competencia(ref)
    if n == 0:
        return "Mesmo mês"
    if n == -12:
        return "Ano anterior"
    if n < 0:
        return "Mês anterior" if n == -1 else f"{-n} meses antes"
    return "Mês seguinte" if n == 1 else f"{n} meses depois"

_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _prazo_label(o: Obrigacao) -> str:
    t = o.regra_prazo_tipo or "ultimo_dia_util"
    if t == "dia_util":
        return f"{o.regra_prazo_dia or 1}º dia útil"
    if t == "primeiro_dia_util":
        return "Primeiro dia útil"
    if t == "dia_fixo":
        return f"Dia {o.regra_prazo_dia or '?'}"
    return "Último dia útil"


def _meses_label(csv: str) -> str:
    nums = [int(x) for x in (csv or "").split(",") if x.strip().isdigit()]
    if len(nums) >= 12:
        return "Todos"
    return ", ".join(_MESES[n - 1] for n in sorted(nums) if 1 <= n <= 12) or "-"


class CopiarModeloRequest(BaseModel):
    origem_empresa_id: int
    destino_empresa_id: int


class DesvincularEmpresaRequest(BaseModel):
    # Sem "todas": a lista é obrigatória e cada obrigação é escolhida na tela.
    # O teto só impede corpo absurdo; o escritório tem dezenas de obrigações.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    # O strip vem ANTES do min_length: sem ele, três espaços passavam e a
    # trilha ficava sem motivo (achado do verificador da fase 36).

    empresa_id: int
    obrigacao_ids: List[int] = Field(min_length=1, max_length=500)
    motivo: str = Field(min_length=3, max_length=500)


class GerarRequest(BaseModel):
    mes: int   # mês de entrega (1-12)
    ano: int
    obrigacao_ids: Optional[List[int]] = None   # vazio = todas as ativas
    empresa_ids: Optional[List[int]] = None     # vazio = todas as que a obrigação alcança


def _set_empresas(db: Session, obrigacao: Obrigacao, empresa_ids):
    if empresa_ids is None:
        return
    empresas = db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all() if empresa_ids else []
    obrigacao.empresas = empresas


@router.get("", response_model=List[ObrigacaoResponse])
def list_obrigacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "ver")),
):
    return db.query(Obrigacao).order_by(Obrigacao.nome.asc()).all()


@router.get("/relatorio")
def relatorio_obrigacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "ver")),
):
    """Relação de obrigações em Excel (nome, setor, empresas, prazo, etc.)."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Obrigações"
    ws.append(["Obrigação", "Mininome", "Setor", "Empresas", "Prazo", "Competência",
               "Meses ativos", "Multa", "Status"])
    for o in db.query(Obrigacao).order_by(Obrigacao.nome.asc()).all():
        empresas = ", ".join(sorted(e.razao_social for e in o.empresas))
        ws.append([
            o.nome, o.mininome or "", o.setor.nome if o.setor else "",
            empresas, _prazo_label(o), _comp_label(o.competencia_ref),
            _meses_label(o.meses_ativos), "Sim" if o.passivel_multa else "Não",
            "Ativa" if o.ativa else "Inativa",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    # Export de massa de verdade: a planilha sai com o cadastro inteiro. A
    # contagem é o que torna a linha útil, porque "exportou" sem tamanho não
    # distingue conferir uma obrigação de levar a base toda embora.
    log_event("EXPORT_DADOS", recurso="obrigacoes", formato="xlsx",
              quantidade=ws.max_row - 1)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=relacao_obrigacoes.xlsx"},
    )


@router.get("/{obrigacao_id}", response_model=ObrigacaoResponse)
def get_obrigacao(
    obrigacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "ver")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    return o


@router.post("/analisar-modelo")
async def analisar_modelo_endpoint(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Analisa um comprovante modelo (PDF) e sugere identificador(es) + CNPJ/competência."""
    from ..services.validador import analisar_modelo
    conteudo = await arquivo.read()
    try:
        return analisar_modelo(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não consegui ler o arquivo: {e}")


@router.post("/gerar")
def gerar_competencia(
    body: GerarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_flag("alocar_obrigacao")),
):
    """Gera as tarefas do mês de entrega informado (empresas da regra ∪ vínculo)."""
    if not (1 <= body.mes <= 12):
        raise HTTPException(status_code=400, detail="Mês inválido (1-12)")
    r = gerar_tarefas(db, body.mes, body.ano, body.obrigacao_ids, body.empresa_ids)
    # Uma linha por clique, e não uma por tarefa: mil linhas por geração afogariam
    # a aba Logs sem dizer nada que a contagem não diga. Só contagem, nunca razão
    # social nem CNPJ. Sai também com zero criadas, porque é a tentativa que se audita.
    log_event("CRIACAO_REGISTRO_CRITICO", tabela="tarefa", lote=True, origem="gerar_mes",
              mes_entrega=r["mes_entrega"], criadas=r["criadas"], puladas=r["puladas"],
              obrigacoes_no_recorte=len(set(body.obrigacao_ids)) if body.obrigacao_ids else None,
              empresas_no_recorte=r["empresas_no_recorte"])
    return r


@router.post("/copiar-empresa")
def copiar_modelo_empresa(
    body: CopiarModeloRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Vincula a empresa-destino a todas as obrigações da empresa-origem."""
    if body.origem_empresa_id == body.destino_empresa_id:
        raise HTTPException(status_code=400, detail="Origem e destino devem ser diferentes")
    destino = db.query(Empresa).filter(Empresa.id == body.destino_empresa_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Empresa de destino não encontrada")

    obrigacoes = (db.query(Obrigacao)
                  .filter(Obrigacao.empresas.any(Empresa.id == body.origem_empresa_id))
                  .all())
    vinculadas = 0
    for o in obrigacoes:
        if destino not in o.empresas:
            o.empresas.append(destino)
            vinculadas += 1
    db.commit()
    # UMA linha, com a contagem: a decisão foi uma só, e registrar cada
    # obrigação viraria dezenas de linhas para um clique.
    log_event("EDICAO_REGISTRO_CRITICO", tabela="obrigacao", lote=True,
              acao="copiar_empresa", quantidade=vinculadas,
              origem_empresa_id=body.origem_empresa_id,
              destino_empresa_id=body.destino_empresa_id)
    return {"message": f"{vinculadas} obrigação(ões) vinculada(s) à empresa destino.",
            "vinculadas": vinculadas, "total_origem": len(obrigacoes)}


def _alcance(db: Session, emp: Empresa) -> dict:
    """{obrigacao: via} das obrigações ativas que alcançam a empresa, sem as que já
    têm exceção para ela. Uma resposta só para a lista da tela e para a
    validação do desvincular: o que a tela oferece é o que a rota aceita."""
    from ..models import ObrigacaoExcecao
    from ..services.gerador import via_alcance
    fora = {x.obrigacao_id for x in db.query(ObrigacaoExcecao.obrigacao_id)
            .filter(ObrigacaoExcecao.empresa_id == emp.id).all()}
    out = {}
    for o in (db.query(Obrigacao).filter(Obrigacao.ativa == True)
              .order_by(Obrigacao.nome).all()):
        via = None if o.id in fora else via_alcance(o, emp)
        if via:
            out[o] = via
    return out


@router.get("/alcance-empresa/{empresa_id}")
def alcance_empresa(empresa_id: int, db: Session = Depends(get_db),
                    current_user: Usuario = Depends(require_flag("alocar_obrigacao"))):
    """Obrigações que alcançam a empresa, por onde, e quantas tarefas em aberto ela tem."""
    from sqlalchemy import func
    from ..models import Tarefa
    from ..services.gerador import ABERTAS
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    abertas = dict(db.query(Tarefa.obrigacao_id, func.count(Tarefa.id))
                   .filter(Tarefa.empresa_id == empresa_id, Tarefa.status.in_(ABERTAS))
                   .group_by(Tarefa.obrigacao_id).all())
    return [{"id": o.id, "nome": o.nome, "via": via, "abertas": abertas.get(o.id, 0)}
            for o, via in _alcance(db, emp).items()]


@router.post("/desvincular-empresa")
def desvincular_empresa(
    body: DesvincularEmpresaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_flag("alocar_obrigacao")),
):
    """A empresa deixa de receber as obrigações escolhidas.

    Tirar só o vínculo não bastava: a obrigação alcança pela regra de regime e
    segmento OU pelo vínculo, e regra vazia quer dizer todas. Por isso, para
    cada obrigação: sai o vínculo à mão, se existe; nasce a exceção, se entra
    pela regra; e as tarefas em aberto dela para a empresa são canceladas como
    "não se aplica". Concluída não muda. Tudo ou nada: uma obrigação fora do
    alcance recusa o pedido inteiro antes de mudar qualquer coisa."""
    from ..services.gerador import aplicar_excecao, cancelar_abertas
    emp = db.query(Empresa).filter(Empresa.id == body.empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    alcance = {o.id: (o, via) for o, via in _alcance(db, emp).items()}
    pedidas = list(dict.fromkeys(body.obrigacao_ids))
    fora = [i for i in pedidas if i not in alcance]
    if fora:
        raise HTTPException(status_code=422,
                            detail="Estas obrigações não alcançam a empresa: "
                                   + ", ".join(str(i) for i in fora))
    motivo = body.motivo.strip()
    excecoes = vinculos = canceladas = 0
    for i in pedidas:
        o, via = alcance[i]
        if via in ("vinculo", "ambos"):
            o.empresas.remove(emp)
            vinculos += 1
        if via in ("regra", "ambos"):
            criada, n = aplicar_excecao(db, o.id, emp.id, motivo, current_user.id)
            excecoes += int(criada)
        else:
            n = cancelar_abertas(db, o.id, emp.id, motivo, current_user.id)
        canceladas += n
    db.commit()
    # Uma linha por clique, com a contagem: muda o que o escritório entrega por
    # aquele cliente, e registrar cada obrigação viraria dezenas de linhas.
    log_event("EDICAO_REGISTRO_CRITICO", tabela="obrigacao", lote=True,
              acao="desvincular_empresa", empresa_id=emp.id, obrigacoes=len(pedidas),
              excecoes_criadas=excecoes, vinculos_removidos=vinculos,
              tarefas_canceladas=canceladas)
    return {"desvinculadas": len(pedidas), "excecoes_criadas": excecoes,
            "vinculos_removidos": vinculos, "tarefas_canceladas": canceladas}


@router.post("", response_model=ObrigacaoResponse, status_code=201)
def create_obrigacao(
    obrigacao: ObrigacaoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    dados = obrigacao.model_dump(exclude={"empresa_ids"})
    o = Obrigacao(**dados)
    _set_empresas(db, o, obrigacao.empresa_ids)
    db.add(o)
    db.commit()
    db.refresh(o)
    log_event("CRIACAO_REGISTRO_CRITICO", tabela="obrigacao",
              alvo_id=o.id, nome=o.nome, empresas=len(o.empresas or []))
    return o


@router.put("/{obrigacao_id}", response_model=ObrigacaoResponse)
def update_obrigacao(
    obrigacao_id: int,
    obrigacao: ObrigacaoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")

    dados = obrigacao.model_dump(exclude_unset=True)
    empresa_ids = dados.pop("empresa_ids", None)
    # Meses vazio (ou null): obrigação antiga que já era vazia no banco segue
    # como está, porque a tela reenvia o que leu e recusar travaria até o
    # renomear. Esvaziar uma que TEM meses é erro: ela pararia de gerar calada.
    if "meses_ativos" in dados and not dados["meses_ativos"]:
        if (o.meses_ativos or "").strip():
            raise HTTPException(status_code=422, detail="Marque ao menos um mês, de 1 a 12.")
        dados.pop("meses_ativos")
    for k, v in dados.items():
        setattr(o, k, v)
    _set_empresas(db, o, empresa_ids)
    db.commit()
    db.refresh(o)
    log_event("EDICAO_REGISTRO_CRITICO", tabela="obrigacao",
              alvo_id=o.id, nome=o.nome, campos=sorted(dados.keys()))
    return o


def _excluir_definitivo(db: Session, o: Obrigacao):
    """Apaga a obrigação, suas tarefas geradas e os vínculos."""
    from ..models import Tarefa
    for t in db.query(Tarefa).filter(Tarefa.obrigacao_id == o.id).all():
        t.responsaveis = []
        db.delete(t)
    o.empresas = []
    db.delete(o)


@router.delete("/{obrigacao_id}")
def delete_obrigacao(
    obrigacao_id: int,
    definitivo: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Sem flag: inativa (mantém histórico). Com `?definitivo=true`: exclui de vez
    (apaga a obrigação e as tarefas já geradas)."""
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    # Um nome só para os dois desfechos: `definitivo` apaga a obrigação e as
    # tarefas geradas, e sem a flag ela apenas fica inativa. A nota trata soft
    # delete dentro do mesmo evento de exclusão.
    alvo = {"tabela": "obrigacao", "alvo_id": o.id, "nome": o.nome}
    if definitivo:
        _excluir_definitivo(db, o)
        db.commit()
        log_event("EXCLUSAO_REGISTRO_CRITICO", level="WARN", inativado=False, **alvo)
        return {"message": "Obrigação excluída"}
    o.ativa = False
    db.commit()
    log_event("EXCLUSAO_REGISTRO_CRITICO", level="WARN", inativado=True, **alvo)
    return {"message": "Obrigação desativada"}


class LoteBody(BaseModel):
    ids: List[int]
    definitivo: bool = True


@router.post("/excluir-lote")
def excluir_lote(
    body: LoteBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Exclui (apaga obrigação + tarefas geradas) ou inativa várias de uma vez."""
    n = 0
    for oid in body.ids:
        o = db.query(Obrigacao).filter(Obrigacao.id == oid).first()
        if not o:
            continue
        if body.definitivo:
            _excluir_definitivo(db, o)
        else:
            o.ativa = False
        n += 1
    db.commit()
    # UMA linha com a contagem, e não uma por obrigação: o lote é uma decisão
    # só, e registrar cada item transformaria uma limpeza de cadastro em
    # dezenas de linhas WARN que ninguém lê até o fim.
    log_event("EXCLUSAO_REGISTRO_CRITICO", level="WARN", tabela="obrigacao",
              lote=True, quantidade=n, pedidas=len(body.ids),
              inativado=not body.definitivo)
    return {"processadas": n}


class StatusBody(BaseModel):
    ativa: bool


@router.post("/{obrigacao_id}/status")
def status_obrigacao(
    obrigacao_id: int,
    body: StatusBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    o.ativa = body.ativa
    db.commit()
    # Este é o caminho lateral do soft delete: mexe no MESMO campo `ativa` que
    # o `DELETE` sem a flag `definitivo` mexe, e aquele já registrava. Sai com
    # o mesmo evento, senão quem filtra exclusão acha um caminho e perde o
    # outro. Reativar é outra coisa, e sai como edição: ressuscitar não é
    # excluir.
    if body.ativa:
        log_event("EDICAO_REGISTRO_CRITICO", tabela="obrigacao",
                  alvo_id=o.id, nome=o.nome, reativada=True)
    else:
        log_event("EXCLUSAO_REGISTRO_CRITICO", level="WARN", tabela="obrigacao",
                  alvo_id=o.id, nome=o.nome, inativado=True)
    return {"message": "Ativada" if body.ativa else "Inativada"}
