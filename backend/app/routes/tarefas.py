from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, func, case
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel
from ..database import get_db
from ..models import Tarefa, Empresa, Setor, Usuario, StatusTarefa
from ..schemas import TarefaCreate, TarefaUpdate, TarefaResponse
from ..auth import (get_current_user, require_perm, require_flag,
                    require_admin, permissao_efetiva)

router = APIRouter(prefix="/tarefas", tags=["tarefas"])


def _escopo_ids(db: Session, user: Usuario):
    """Ids de responsáveis visíveis ao usuário conforme escopo_tarefas.
    Retorna None quando o escopo é 'todas' (sem filtro)."""
    from ..services.substituicao import originais_cobertos
    escopo = permissao_efetiva(user).get("escopo_tarefas", "todas")
    if escopo == "todas":
        return None
    ids = {user.id}
    if escopo == "setor":
        # 'setor' = própria equipe (subordinados diretos via gestor_id)
        for (sid,) in db.query(Usuario.id).filter(Usuario.gestor_id == user.id).all():
            ids.add(sid)
    # quem este usuário está cobrindo agora (substituição temporária) também entra no escopo
    ids |= originais_cobertos(db, user.id)
    return ids


def _aplicar_escopo(query, db: Session, user: Usuario):
    # Bloqueados somem: tarefas de empresa bloqueada ou de responsável bloqueado não aparecem.
    query = query.filter(~Tarefa.empresa.has(Empresa.bloqueado == True))
    query = query.filter(~Tarefa.responsavel.has(Usuario.bloqueado == True))
    ids = _escopo_ids(db, user)
    if ids is not None:
        query = query.filter(or_(
            Tarefa.responsavel_id.in_(ids),
            Tarefa.supervisor_id.in_(ids),
            Tarefa.responsaveis.any(Usuario.id.in_(ids)),
        ))
    return query


def _no_escopo(tarefa: Tarefa, db: Session, user: Usuario) -> bool:
    ids = _escopo_ids(db, user)
    if ids is None:
        return True
    return (tarefa.responsavel_id in ids
            or tarefa.supervisor_id in ids
            or any(u.id in ids for u in tarefa.responsaveis))


def _aplicar_responsaveis(db: Session, db_tarefa: Tarefa, responsavel_ids):
    """Define os responsáveis (M2M) e sincroniza o principal (responsavel_id)."""
    users = (db.query(Usuario).filter(Usuario.id.in_(responsavel_ids)).all()
             if responsavel_ids else [])
    db_tarefa.responsaveis = users
    db_tarefa.responsavel_id = users[0].id if users else None


class TransferirRequest(BaseModel):
    responsavel_id: int


class CopiarTarefasRequest(BaseModel):
    origem_empresa_id: int
    destino_empresa_id: int

@router.get("/dashboard/stats")
def get_dashboard_stats(
    empresa_id: int = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)

    query = _aplicar_escopo(db.query(Tarefa), db, current_user)
    if empresa_id:
        query = query.filter(Tarefa.empresa_id == empresa_id)

    total = query.count()
    pendentes = query.filter(Tarefa.status == StatusTarefa.PENDENTE).count()
    em_andamento = query.filter(Tarefa.status == StatusTarefa.EM_ANDAMENTO).count()
    concluidas = query.filter(Tarefa.status == StatusTarefa.CONCLUIDA).count()
    atrasadas = query.filter(
        and_(
            Tarefa.data_prazo < now,
            Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
        )
    ).count()
    vencendo_hoje = query.filter(
        and_(
            Tarefa.data_prazo >= today_start,
            Tarefa.data_prazo <= today_start + timedelta(days=1),
            Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
        )
    ).count()
    vencendo_semana = query.filter(
        and_(
            Tarefa.data_prazo >= today_start,
            Tarefa.data_prazo <= week_end,
            Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
        )
    ).count()

    return {
        "total_tarefas": total,
        "pendentes": pendentes,
        "em_andamento": em_andamento,
        "concluidas": concluidas,
        "atrasadas": atrasadas,
        "vencendo_hoje": vencendo_hoje,
        "vencendo_semana": vencendo_semana
    }


@router.get("/dashboard/stats-por-setor")
def get_dashboard_stats_por_setor(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Distribuição de status por setor: um bloco por setor para os donuts.

    Uma consulta só, agrupada por setor. Antes era um laço: para cada setor,
    cinco `count()` mais a montagem do escopo -- num escritório com dez setores,
    sessenta idas ao banco para desenhar uns gráficos de rosca. O trabalho é
    todo de contagem condicional, e SQL faz isso num `GROUP BY`.
    """
    now = datetime.utcnow()

    def _quando(condicao):
        """1 quando a linha satisfaz, 0 quando não -- somado vira contagem."""
        return func.sum(case((condicao, 1), else_=0))

    atrasada = and_(
        Tarefa.data_prazo < now,
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
    )

    linhas = (_aplicar_escopo(
        db.query(
            Setor.id.label("setor_id"),
            Setor.nome.label("setor_nome"),
            func.count(Tarefa.id).label("total"),
            _quando(Tarefa.status == StatusTarefa.PENDENTE).label("pendentes"),
            _quando(Tarefa.status == StatusTarefa.EM_ANDAMENTO).label("em_andamento"),
            _quando(Tarefa.status == StatusTarefa.CONCLUIDA).label("concluidas"),
            _quando(atrasada).label("atrasadas"),
        ).join(Setor, Tarefa.setor_id == Setor.id), db, current_user)
        .group_by(Setor.id, Setor.nome)
        .order_by(Setor.nome)
        .all())

    # Setor sem tarefa não vira donut -- com o join, ele nem chega aqui.
    return [{
        "setor_id": l.setor_id,
        "setor_nome": l.setor_nome,
        "total_tarefas": int(l.total or 0),
        "pendentes": int(l.pendentes or 0),
        "em_andamento": int(l.em_andamento or 0),
        "concluidas": int(l.concluidas or 0),
        "atrasadas": int(l.atrasadas or 0),
    } for l in linhas]

@router.get("/{tarefa_id}/link-envio")
def link_envio(
    tarefa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Link público (com token) para o cliente enviar o comprovante desta tarefa."""
    t = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    from ..services import upload as up, config as cfgmod
    return {"link": up.link_publico(cfgmod.carregar(db), t, db)}


@router.get("", response_model=List[TarefaResponse])
def list_tarefas(
    empresa_id: int = None,
    setor_id: int = None,
    responsavel_id: int = None,
    status: StatusTarefa = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    query = _aplicar_escopo(db.query(Tarefa), db, current_user)

    if empresa_id:
        query = query.filter(Tarefa.empresa_id == empresa_id)
    if setor_id:
        query = query.filter(Tarefa.setor_id == setor_id)
    if responsavel_id:
        query = query.filter(Tarefa.responsavel_id == responsavel_id)
    if status:
        query = query.filter(Tarefa.status == status)

    # Sem estes carregamentos a listagem vira N+1: `TarefaResponse` expõe
    # `responsaveis` e `supervisor`, e o Pydantic ia buscar cada um no banco na
    # hora de serializar -- uma query POR TAREFA. Medido antes de corrigir: 500
    # tarefas = 503 queries. Em SQLite local isso custava 78 ms e passava
    # despercebido; contra o Postgres do servidor, cada uma é um ida-e-volta de
    # rede, e a tela levava segundos.
    #
    # `selectinload` (não joinedload) para os responsáveis, porque é uma coleção:
    # o join multiplicaria as linhas da tarefa pelo número de responsáveis.
    return (query
            .options(
                joinedload(Tarefa.obrigacao),      # exige_documento lê a obrigação
                joinedload(Tarefa.setor),          # setor_nome, idem
                joinedload(Tarefa.supervisor),
                selectinload(Tarefa.responsaveis),
            )
            .order_by(Tarefa.data_prazo.asc())
            .all())

@router.get("/{tarefa_id}", response_model=TarefaResponse)
def get_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa or not _no_escopo(tarefa, db, current_user):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return tarefa

@router.post("", response_model=TarefaResponse, status_code=201)
def create_tarefa(
    tarefa: TarefaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("tarefas", "editar"))
):
    empresa = db.query(Empresa).filter(Empresa.id == tarefa.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if tarefa.setor_id:
        setor = db.query(Setor).filter(Setor.id == tarefa.setor_id).first()
        if not setor:
            raise HTTPException(status_code=404, detail="Setor não encontrado")

    dados = tarefa.model_dump(exclude={"responsavel_ids"})
    db_tarefa = Tarefa(**dados)
    _aplicar_responsaveis(db, db_tarefa, tarefa.responsavel_ids)
    db.add(db_tarefa)
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

@router.put("/{tarefa_id}", response_model=TarefaResponse)
def update_tarefa(
    tarefa_id: int,
    tarefa: TarefaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("tarefas", "editar"))
):
    db_tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    # Fora do escopo → 404 (não vaza existência de tarefa de outro).
    if not db_tarefa or not _no_escopo(db_tarefa, db, current_user):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    perm = permissao_efetiva(current_user)
    update_data = tarefa.model_dump(exclude_unset=True)
    eh_admin = current_user.grupo == "admin"

    # Datas de prazo (interno) e de vencimento: SÓ admin altera.
    if ("data_vencimento" in update_data
            and update_data["data_vencimento"] != db_tarefa.data_vencimento
            and not eh_admin):
        raise HTTPException(status_code=403, detail="Apenas administrador pode alterar a data de vencimento.")
    if ("data_prazo" in update_data
            and update_data["data_prazo"] != db_tarefa.data_prazo
            and not eh_admin):
        raise HTTPException(status_code=403, detail="Apenas administrador pode alterar o prazo interno.")
    if (update_data.get("status") == StatusTarefa.CANCELADA
            and db_tarefa.status != StatusTarefa.CANCELADA
            and not perm.get("dispensar_demanda")):
        raise HTTPException(status_code=403, detail="Sem permissão para dispensar/cancelar a demanda")

    # Baixa: tarefa que exige documento só conclui pelo e-validador (com anexo).
    if (update_data.get("status") == StatusTarefa.CONCLUIDA
            and db_tarefa.status != StatusTarefa.CONCLUIDA
            and not db_tarefa.anexo_nome
            and db_tarefa.exige_documento):
        raise HTTPException(
            status_code=403,
            detail="Esta tarefa exige validação de documento: baixe pelo e-validador. Baixa manual não é permitida.")

    if tarefa.status == StatusTarefa.CONCLUIDA and not db_tarefa.data_conclusao:
        update_data["data_conclusao"] = datetime.utcnow()

    # responsaveis (M2M) tratado à parte — trocar o dono é só gestor/admin.
    if "responsavel_ids" in update_data:
        novos = set(update_data.get("responsavel_ids") or [])
        atuais = {u.id for u in db_tarefa.responsaveis}
        if novos != atuais and current_user.grupo not in ("admin", "gestor"):
            raise HTTPException(status_code=403, detail="Apenas gestor ou admin pode trocar o responsável.")
        _aplicar_responsaveis(db, db_tarefa, update_data.pop("responsavel_ids"))

    for key, value in update_data.items():
        setattr(db_tarefa, key, value)

    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

# Aberto no navegador x salvo em disco. PDF e imagem são para conferir na hora;
# planilha o navegador não renderiza, então baixar é o único desfecho útil.
_INLINE = {".pdf": "application/pdf", ".png": "image/png",
           ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@router.get("/{tarefa_id}/anexo")
def baixar_anexo(
    tarefa_id: int,
    baixar: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Devolve o comprovante que baixou a tarefa.

    Até aqui o arquivo entrava e não saía: ficava no volume, com o nome no
    banco, e nenhuma rota o servia. Era a prova da entrega guardada num lugar de
    onde ninguém tirava — e prova de entrega é justamente o que se pede numa
    fiscalização.

    O escopo é o MESMO da listagem de tarefas: quem enxerga a tarefa enxerga o
    comprovante dela. Não há permissão nova a administrar, e ninguém passa a ver
    documento de tarefa que já não podia ver.

    Tarefa fora do escopo e tarefa inexistente saem pela mesma porta (404). Um
    403 aqui contaria a quem não deveria que aquela tarefa existe.
    """
    import os
    from ..services import upload as up

    tarefa = (_aplicar_escopo(db.query(Tarefa), db, current_user)
              .filter(Tarefa.id == tarefa_id).first())
    if not tarefa or not tarefa.anexo_nome:
        raise HTTPException(status_code=404, detail="Comprovante não encontrado")

    caminho = up.caminho_do_anexo(tarefa.anexo_nome)
    if not caminho:
        # O banco aponta para um arquivo que não está mais no volume. Dizer isso
        # em vez de um 404 seco: some depois de restaurar backup sem o volume, e
        # o time precisa saber que é o arquivo que sumiu, não a tarefa.
        raise HTTPException(status_code=410,
                            detail="O arquivo não está mais no armazenamento.")

    nome = up.nome_de_exibicao(tarefa.anexo_nome)
    ext = os.path.splitext(nome)[1].lower()
    tipo = _INLINE.get(ext, "application/octet-stream")
    disposicao = "attachment" if (baixar or ext not in _INLINE) else "inline"
    return FileResponse(caminho, media_type=tipo, filename=nome,
                        content_disposition_type=disposicao)


# ── Documento que o escritório ENTREGA ao cliente ────────────────────────────
#
# O caminho contrário do e-validador: em vez de esperar o comprovante do
# cliente, a tarefa carrega uma guia, um boleto ou um relatório e o envia.
# Guia do Simples é o caso típico, e é recorrente como qualquer outra obrigação.

EXT_SAIDA_OK = {".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".xml", ".zip", ".csv", ".txt"}
MAX_SAIDA = 15 * 1024 * 1024


def _tarefa_no_escopo(db, user, tarefa_id):
    t = (_aplicar_escopo(db.query(Tarefa), db, user)
         .filter(Tarefa.id == tarefa_id).first())
    if not t:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return t


@router.post("/{tarefa_id}/saida")
async def anexar_saida(
    tarefa_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Anexa à tarefa o documento que será entregue ao cliente.

    Anexar NÃO envia. São dois passos porque mandar documento para cliente é
    irreversível: uma guia errada que sai não volta, e o intervalo entre anexar
    e enviar é onde se confere o arquivo.
    """
    import os
    from ..services import upload as up

    tarefa = _tarefa_no_escopo(db, current_user, tarefa_id)
    nome = arquivo.filename or "documento"
    ext = os.path.splitext(nome)[1].lower()
    if ext not in EXT_SAIDA_OK:
        raise HTTPException(status_code=400,
                            detail=f"Tipo não aceito ({ext or 'sem extensão'}). "
                                   f"Aceitos: {', '.join(sorted(EXT_SAIDA_OK))}")
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > MAX_SAIDA:
        raise HTTPException(status_code=400,
                            detail=f"Arquivo acima de {MAX_SAIDA // (1024 * 1024)} MB.")

    # Trocar o documento apaga o anterior: guia retificada substitui a errada, e
    # deixar as duas no volume só cria dúvida sobre qual é a boa.
    if tarefa.saida_nome and tarefa.saida_nome != nome:
        up.remover_arquivo(tarefa.saida_nome)
    tarefa.saida_nome = up.salvar_saida(tarefa.id, nome, conteudo)
    db.commit()
    return {"arquivo": up.nome_de_exibicao(tarefa.saida_nome), "bytes": len(conteudo)}


@router.get("/{tarefa_id}/saida")
def baixar_saida(
    tarefa_id: int,
    baixar: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Devolve o documento anexado para entrega — para conferir antes de enviar."""
    import os
    from ..services import upload as up

    tarefa = _tarefa_no_escopo(db, current_user, tarefa_id)
    if not tarefa.saida_nome:
        raise HTTPException(status_code=404, detail="Nenhum documento anexado")
    caminho = up.caminho_do_anexo(tarefa.saida_nome)
    if not caminho:
        raise HTTPException(status_code=410, detail="O arquivo não está mais no armazenamento.")
    nome = up.nome_de_exibicao(tarefa.saida_nome)
    ext = os.path.splitext(nome)[1].lower()
    tipo = _INLINE.get(ext, "application/octet-stream")
    return FileResponse(caminho, media_type=tipo, filename=nome,
                        content_disposition_type="attachment" if (baixar or ext not in _INLINE) else "inline")


@router.get("/{tarefa_id}/envios")
def historico_envios(
    tarefa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Toda vez que o documento saiu, com data, canal e destinatário."""
    from ..models import TarefaEnvio
    _tarefa_no_escopo(db, current_user, tarefa_id)
    envios = (db.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == tarefa_id)
              .order_by(TarefaEnvio.enviado_em.desc()).all())
    return [{"id": e.id, "arquivo": e.arquivo, "canal": e.canal, "endereco": e.endereco,
             "destinatario": e.destinatario, "sucesso": e.sucesso, "detalhe": e.detalhe,
             "enviado_em": e.enviado_em} for e in envios]


@router.post("/{tarefa_id}/enviar-cliente")
async def enviar_ao_cliente(
    tarefa_id: int,
    ensaio: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Entrega o documento anexado ao cliente e conclui a tarefa.

    Vai para os contatos da EMPRESA e para os USUÁRIOS do tipo cliente ligados
    a ela, sem repetir endereço.

    A tarefa só é concluída se ALGUÉM recebeu. Concluir com todos os envios
    falhando registraria como entregue um documento que não chegou a ninguém —
    e o erro só apareceria quando o cliente reclamasse da multa.

    `ensaio=true` mostra a lista de destinatários sem enviar nada.
    """
    from ..models import TarefaEnvio
    from ..services import upload as up, config as cfgmod
    from ..services.whatsapp import (destinatarios_cliente, send_whatsapp_document,
                                     carregar_zap)
    from ..services.email import send_email
    from datetime import datetime

    tarefa = _tarefa_no_escopo(db, current_user, tarefa_id)
    if not tarefa.saida_nome:
        raise HTTPException(status_code=400, detail="Anexe o documento antes de enviar.")
    try:
        conteudo = up.ler_arquivo_salvo(tarefa.saida_nome)
    except FileNotFoundError:
        raise HTTPException(status_code=410, detail="O arquivo não está mais no armazenamento.")

    destinos = destinatarios_cliente(db, tarefa)
    if not destinos:
        raise HTTPException(
            status_code=400,
            detail="A empresa não tem e-mail nem telefone, e não há usuário do tipo "
                   "cliente vinculado a ela. Sem isso não há para onde enviar.")
    if ensaio:
        return {"ensaio": True, "arquivo": up.nome_de_exibicao(tarefa.saida_nome),
                "destinatarios": destinos}

    cfg = cfgmod.carregar(db)
    nome_arquivo = up.nome_de_exibicao(tarefa.saida_nome)
    empresa = tarefa.empresa.razao_social if tarefa.empresa else ""
    comp = f" — {tarefa.competencia}" if tarefa.competencia else ""
    assunto = f"[BPS4] {tarefa.titulo}{comp}"
    texto = (f"Olá,\n\nSegue {tarefa.titulo}{comp} referente a {empresa}.\n\n"
             f"Arquivo: {nome_arquivo}\n\nQualquer dúvida, estamos à disposição.")
    # O documento do cliente não vai para atendente do escritório: quem recebe é
    # o cliente, e o atendimento nasce na fila padrão da conexão.
    zap = await carregar_zap(cfg)

    resultados = []
    for d in destinos:
        if d["canal"] == "whatsapp":
            r = await send_whatsapp_document(d["endereco"], nome_arquivo, conteudo,
                                             texto, cfg)
        else:
            r = send_email(d["endereco"], assunto, texto, cfg,
                           anexos=[(nome_arquivo, conteudo)])
        ok = bool(r.get("success"))
        db.add(TarefaEnvio(tarefa_id=tarefa.id, arquivo=nome_arquivo, canal=d["canal"],
                           endereco=d["endereco"], destinatario=d["nome"], sucesso=ok,
                           detalhe=None if ok else str(r.get("error") or r.get("response") or "")[:500],
                           enviado_por=current_user.id))
        resultados.append({**d, "enviado": ok, "detalhe": r})

    entregou = any(r["enviado"] for r in resultados)
    if entregou:
        tarefa.status = StatusTarefa.CONCLUIDA
        tarefa.data_conclusao = datetime.utcnow()
        tarefa.data_entrega = tarefa.data_entrega or datetime.utcnow()
    db.commit()

    enviados = sum(1 for r in resultados if r["enviado"])
    return {
        "arquivo": nome_arquivo,
        "enviados": enviados,
        "falhas": len(resultados) - enviados,
        "concluiu": entregou,
        "message": (f"{enviados} de {len(resultados)} envio(s) concluído(s)."
                    + (" Tarefa concluída." if entregou
                       else " Nenhum envio funcionou — a tarefa segue aberta.")),
        "resultados": resultados,
    }


@router.post("/copiar")
def copiar_tarefas(
    body: CopiarTarefasRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_flag("alocar_obrigacao"))
):
    if body.origem_empresa_id == body.destino_empresa_id:
        raise HTTPException(status_code=400, detail="Origem e destino devem ser empresas diferentes")

    destino = db.query(Empresa).filter(Empresa.id == body.destino_empresa_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Empresa de destino não encontrada")

    origem_tarefas = db.query(Tarefa).filter(
        Tarefa.empresa_id == body.origem_empresa_id,
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
    ).all()

    copiadas = 0
    for t in origem_tarefas:
        # Copia como modelo: sem datas; setor interno é mantido.
        nova = Tarefa(
            titulo=t.titulo,
            descricao=t.descricao,
            empresa_id=body.destino_empresa_id,
            setor_id=t.setor_id,
            responsavel_id=t.responsavel_id,
            supervisor_id=t.supervisor_id,
            prioridade=t.prioridade,
            gera_multa=t.gera_multa,
            observacoes=t.observacoes,
            status=StatusTarefa.PENDENTE,
            data_prazo=None,
            data_vencimento=None,
        )
        nova.responsaveis = list(t.responsaveis)
        db.add(nova)
        copiadas += 1

    db.commit()
    return {"message": f"{copiadas} tarefa(s) copiada(s) como modelo (defina os prazos depois).", "copiadas": copiadas}


@router.post("/{tarefa_id}/transferir", response_model=TarefaResponse)
def transferir_tarefa(
    tarefa_id: int,
    body: TransferirRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("tarefas", "editar"))
):
    if current_user.grupo not in ("admin", "gestor"):
        raise HTTPException(status_code=403, detail="Apenas gestor ou admin pode trocar o responsável.")
    db_tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not db_tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    novo_resp = db.query(Usuario).filter(Usuario.id == body.responsavel_id, Usuario.ativo == True).first()
    if not novo_resp:
        raise HTTPException(status_code=404, detail="Novo responsável não encontrado")

    db_tarefa.responsaveis = [novo_resp]
    db_tarefa.responsavel_id = novo_resp.id
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa


@router.delete("/{tarefa_id}")
def delete_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_flag("dispensar_demanda"))
):
    db_tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not db_tarefa or not _no_escopo(db_tarefa, db, current_user):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    # Dois passos, de propósito: a primeira vez CANCELA (reversível, e o
    # histórico fica); a segunda, numa tarefa já cancelada, EXCLUI de vez.
    # Antes só existia o primeiro passo, e tarefa cancelada não tinha saída --
    # a lixeira prometia excluir e cancelava de novo, para sempre.
    if db_tarefa.status == StatusTarefa.CANCELADA:
        from ..services import upload as up
        arquivo = db_tarefa.anexo_nome
        db_tarefa.responsaveis = []          # solta a associação antes
        db.delete(db_tarefa)
        db.commit()
        # o comprovante sai do volume junto: sem a tarefa, ninguém mais o acha
        removido = up.remover_arquivo(arquivo)
        return {"message": "Tarefa excluída definitivamente.",
                "excluida": True, "anexo_removido": removido}

    db_tarefa.status = StatusTarefa.CANCELADA
    db.commit()
    return {"message": "Tarefa cancelada. Para excluir de vez, use a lixeira de novo.",
            "excluida": False}


class ExcluirCompetenciaBody(BaseModel):
    competencia: str  # "MM/AAAA"


@router.post("/excluir-competencia")
def excluir_tarefas_competencia(
    body: ExcluirCompetenciaBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """Apaga DE VEZ as tarefas geradas por obrigação (com obrigacao_id) da
    competência informada (MM/AAAA). É o desfazer do 'Gerar tarefas do mês', e
    depois dá para regerar limpo. Não toca em tarefas avulsas (criadas à mão)."""
    comp = (body.competencia or "").strip()
    p = comp.split("/")
    valido = (len(p) == 2 and p[0].isdigit() and p[1].isdigit()
              and len(p[0]) == 2 and len(p[1]) == 4 and 1 <= int(p[0]) <= 12)
    if not valido:
        raise HTTPException(status_code=400, detail="Competência inválida (use MM/AAAA)")
    tarefas = (db.query(Tarefa)
               .filter(Tarefa.competencia == comp, Tarefa.obrigacao_id.isnot(None))
               .all())
    n = 0
    for t in tarefas:
        t.responsaveis = []
        db.delete(t)
        n += 1
    db.commit()
    return {"excluidas": n, "competencia": comp}
