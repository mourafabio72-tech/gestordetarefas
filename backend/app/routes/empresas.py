from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..database import get_db
from ..models import (Empresa, Usuario, Setor, EmpresaSetorResponsavel,
                      empresa_setor_resp_usuarios)
from ..schemas import EmpresaCreate, EmpresaResponse
from ..auth import get_current_user, require_perm
from ..seguranca import log_event, ip_cliente
from ..services import importador_empresas as imp
from ..services import resp_setor
from ..services.validacao import cnpj_valido


def _empresa_em_uso(db: Session, eid: int) -> int:
    from ..models import Tarefa, obrigacao_empresa
    n = db.query(Tarefa).filter(Tarefa.empresa_id == eid).count()
    n += db.query(obrigacao_empresa).filter(obrigacao_empresa.c.empresa_id == eid).count()
    n += db.query(Usuario).filter(Usuario.empresa_id == eid).count()
    return n

router = APIRouter(prefix="/empresas", tags=["empresas"])


class BloquearRequest(BaseModel):
    bloqueado: bool = True


# Teto de quantas pessoas cabem num par (empresa, setor). A vault NÃO tem regra
# para tamanho de lista em payload JSON (procurado e não encontrado, ver
# 00_GENESIS/NOTAS_LIDAS.md), então o número é decisão local e fica no código,
# como MAX_TENTATIVAS já é. O setor maior do escritório não chega perto disso:
# o teto existe para barrar payload absurdo, não para limitar o cadastro.
MAX_RESP_POR_SETOR = 20


class RespSetorItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setor_id: int
    responsavel_id: Optional[int] = None   # legado: a tela antiga manda um só
    responsavel_ids: List[int] = Field(default_factory=list,
                                       max_length=MAX_RESP_POR_SETOR)

    @field_validator("responsavel_id", mode="before")
    @classmethod
    def _sem_dono(cls, v):
        """Select sem escolha manda "" — isso é "sem dono ainda", não erro.

        Mesmo caso do marco de fechamento na empresa: campo vazio de formulário
        chegava como texto num campo inteiro e derrubava o salvamento inteiro
        num 422, que a tela mostrava como "[object Object]".
        """
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("responsavel_ids")
    @classmethod
    def _sem_repetido(cls, v):
        """Id repetido colapsa, preservando a ordem de quem apareceu primeiro.

        Não é erro: a tela pode mandar a mesma pessoa duas vezes num clique
        duplo, e recusar o salvamento inteiro por isso seria pior do que
        guardar a lista sem a repetição."""
        vistos, saida = set(), []
        for i in v:
            if i not in vistos:
                vistos.add(i)
                saida.append(i)
        return saida

    def ids(self) -> List[int]:
        """A lista escolhida, com o campo antigo servindo de entrada de um só.

        O primeiro da lista é o PRINCIPAL. Enquanto a tela não manda
        `responsavel_ids` (fase 11), o `responsavel_id` sozinho continua
        valendo, e o comportamento não muda para quem ainda salva pelo formato
        antigo."""
        if self.responsavel_ids:
            return list(self.responsavel_ids)
        return [self.responsavel_id] if self.responsavel_id is not None else []


class RespSetorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: List[RespSetorItem]             # SOMENTE os setores que a empresa ATENDE


@router.get("/modelo-responsaveis")
def modelo_responsaveis(db: Session = Depends(get_db),
                        current_user: Usuario = Depends(require_perm("empresas", "editar"))):
    from ..services import importador_resp_setor as impr
    return Response(
        content=impr.gerar_modelo(db),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_responsaveis_setor.xlsx"},
    )


@router.post("/importar-responsaveis")
async def importar_responsaveis(
    arquivo: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar")),
):
    from ..services import importador_resp_setor as impr
    conteudo = await arquivo.read()
    try:
        saida = impr.importar(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler a planilha: {e}")
    # A planilha regrava a mesma matriz que o PUT, e em muitas empresas de uma
    # vez. Mutação de dado crítico deixa rastro pelos dois caminhos, não só pelo
    # da tela.
    log_event("EDICAO_REGISTRO_CRITICO", tabela="empresa_setor_responsavel",
              origem="planilha", user_id=current_user.id, ip=ip_cliente(request),
              resumo=saida.get("resumo"))
    return saida


@router.get("/{empresa_id}/responsaveis-setor")
def get_responsaveis_setor(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "ver")),
):
    """Um item por setor ATIVO: se a empresa atende + os responsáveis.
    Empresa nunca configurada (0 linhas) = atende todos (retrocompatível).

    Devolve `responsavel_ids` (a lista) e `responsavel_id` (o primeiro dela),
    porque a tela antiga e o importador ainda leem o campo de um só."""
    vinculos = (db.query(EmpresaSetorResponsavel)
                .options(selectinload(EmpresaSetorResponsavel.responsaveis))
                .filter(EmpresaSetorResponsavel.empresa_id == empresa_id).all())
    linhas = {v.setor_id: v for v in vinculos}
    nunca_config = len(linhas) == 0
    setores = db.query(Setor).filter(Setor.ativo == True).order_by(Setor.nome).all()
    saida = []
    for s in setores:
        v = linhas.get(s.id)
        ids = [u.id for u in v.responsaveis] if v else []
        saida.append({"setor_id": s.id, "setor_nome": s.nome,
                      "atende": nunca_config or (s.id in linhas),
                      "responsavel_id": v.responsavel_id if v else None,
                      "responsavel_ids": ids})
    return saida


@router.put("/{empresa_id}/responsaveis-setor")
def set_responsaveis_setor(
    empresa_id: int,
    body: RespSetorBody,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar")),
):
    """Regrava a matriz. Presença da linha = a empresa ATENDE aquele setor.
    `itens` traz só os atendidos; os demais são removidos (não geram tarefa).

    Tudo que vem no corpo é validado ANTES de qualquer gravação, como manda
    `Padrao_IDOR`: id de setor e id de pessoa chegam pelo body, e body é
    território do cliente igual à URL. Recusa devolve 404 e não 403, para não
    confirmar que o id existe."""
    if not db.query(Empresa).filter(Empresa.id == empresa_id).first():
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    setores_ok = {s.id for s in db.query(Setor.id).filter(Setor.ativo == True).all()}
    vistos = set()
    for it in body.itens:
        if it.setor_id not in setores_ok:
            raise HTTPException(status_code=404, detail="Setor não encontrado")
        if it.setor_id in vistos:
            raise HTTPException(status_code=422, detail="Setor repetido na lista")
        vistos.add(it.setor_id)

    pedidos = {uid for it in body.itens for uid in it.ids()}
    if pedidos:
        achados = db.query(Usuario).filter(Usuario.id.in_(pedidos)).all()
        # Elegível é colaborador ativo e não bloqueado. Avaliado em Python de
        # propósito: `tipo`, `bloqueado` e `ativo` são NULL em conta antiga, e
        # comparação com NULL no SQL some com a linha em vez de recusá-la.
        elegiveis = {u.id for u in achados
                     if (u.tipo or "colaborador") != "cliente"
                     and not u.bloqueado and u.ativo is not False}
        if pedidos - elegiveis:
            raise HTTPException(status_code=404, detail="Responsável não encontrado")

    antigos = db.query(EmpresaSetorResponsavel.id).filter(
        EmpresaSetorResponsavel.empresa_id == empresa_id).all()
    if antigos:
        # A associativa sai ANTES dos vínculos. `query().delete()` é DELETE em
        # massa: não passa pelo ORM, então não limpa a tabela do meio sozinho e
        # deixaria linha órfã apontando para vínculo que não existe mais. Foi
        # exatamente esse o 500 de 2026-09-03 na exclusão de tarefas.
        db.execute(empresa_setor_resp_usuarios.delete().where(
            empresa_setor_resp_usuarios.c.vinculo_id.in_([a.id for a in antigos])))
    db.query(EmpresaSetorResponsavel).filter(
        EmpresaSetorResponsavel.empresa_id == empresa_id).delete()

    total = 0
    for it in body.itens:
        ids = it.ids()
        total += len(ids)
        vinculo = EmpresaSetorResponsavel(empresa_id=empresa_id, setor_id=it.setor_id)
        db.add(vinculo)
        resp_setor.gravar(db, vinculo, ids)
    db.commit()
    log_event("EDICAO_REGISTRO_CRITICO", tabela="empresa_setor_responsavel",
              empresa_id=empresa_id, user_id=current_user.id,
              ip=ip_cliente(request), setores=len(body.itens), responsaveis=total)
    return {"ok": True}


@router.get("/modelo-importacao")
def modelo_importacao(current_user: Usuario = Depends(require_perm("empresas", "editar"))):
    conteudo = imp.gerar_modelo()
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_importacao_empresas.xlsx"},
    )


@router.post("/importar")
async def importar_empresas(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar")),
):
    conteudo = await arquivo.read()
    try:
        return imp.importar(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler a planilha: {e}")

@router.get("", response_model=List[EmpresaResponse])
def list_empresas(
    todas: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Por padrão só as ativas (dropdowns pelo app). `todas=true` inclui inativas
    (usado no cadastro de Empresas, que filtra por situação)."""
    q = db.query(Empresa)
    if not todas:
        q = q.filter(Empresa.ativo == True)
    return q.all()

@router.get("/{empresa_id}", response_model=EmpresaResponse)
def get_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa

@router.post("", response_model=EmpresaResponse, status_code=201)
def create_empresa(
    empresa: EmpresaCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    if empresa.cnpj:
        if not cnpj_valido(empresa.cnpj):
            raise HTTPException(status_code=400, detail="CNPJ inválido (dígitos verificadores não conferem).")
        existing = db.query(Empresa).filter(Empresa.cnpj == empresa.cnpj).first()
        if existing:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    db_empresa = Empresa(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)

    # Vínculo automático: gera já as tarefas do mês para as obrigações cuja
    # regra (regime/segmento) casa com esta empresa. Falha aqui não quebra o cadastro.
    try:
        from ..services import gerador
        res = gerador.gerar_empresa_mes_atual(db, db_empresa)
        response.headers["X-Tarefas-Geradas"] = str(res.get("criadas", 0))
    except Exception:
        db.rollback()
        response.headers["X-Tarefas-Geradas"] = "0"
    return db_empresa

@router.put("/{empresa_id}", response_model=EmpresaResponse)
def update_empresa(
    empresa_id: int,
    empresa: EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if empresa.cnpj and not cnpj_valido(empresa.cnpj):
        raise HTTPException(status_code=400, detail="CNPJ inválido (dígitos verificadores não conferem).")

    for key, value in empresa.model_dump(exclude_unset=True).items():
        setattr(db_empresa, key, value)

    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@router.post("/{empresa_id}/bloquear", response_model=EmpresaResponse)
def bloquear_empresa(
    empresa_id: int,
    body: BloquearRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    emp.bloqueado = body.bloqueado
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/{empresa_id}")
def delete_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if _empresa_em_uso(db, empresa_id) > 0:
        db_empresa.ativo = False
        db.commit()
        return {"message": "Empresa tem tarefas/obrigações/usuários vinculados, então foi inativada e não excluída.", "inativado": True}
    db.delete(db_empresa)
    db.commit()
    return {"message": "Empresa excluída.", "inativado": False}