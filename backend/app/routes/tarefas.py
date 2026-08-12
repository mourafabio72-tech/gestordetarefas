from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel
from ..database import get_db
from ..models import Tarefa, Empresa, Setor, Usuario, StatusTarefa, Obrigacao
from ..schemas import TarefaCreate, TarefaUpdate, TarefaResponse
from ..auth import (get_current_user, require_perm, require_flag,
                    permissao_efetiva)

router = APIRouter(prefix="/tarefas", tags=["tarefas"])


def _exige_documento(obrig: Obrigacao) -> bool:
    """Tarefa exige baixa por documento (e-validador)? A flag manda; NULL deriva
    de 'identificadores' (se a obrigação tem o que validar, exige documento)."""
    if obrig is None:
        return False
    if obrig.exige_documento is None:
        return bool((obrig.identificadores or "").strip())
    return bool(obrig.exige_documento)


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
    """Distribuição de status por setor — um bloco por setor para os donuts."""
    now = datetime.utcnow()
    resultado = []
    for setor in db.query(Setor).order_by(Setor.nome).all():
        base = _aplicar_escopo(db.query(Tarefa), db, current_user).filter(Tarefa.setor_id == setor.id)
        total = base.count()
        if total == 0:
            continue  # setor sem tarefas não vira donut
        atrasadas = base.filter(and_(
            Tarefa.data_prazo < now,
            Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
        )).count()
        resultado.append({
            "setor_id": setor.id,
            "setor_nome": setor.nome,
            "total_tarefas": total,
            "pendentes": base.filter(Tarefa.status == StatusTarefa.PENDENTE).count(),
            "em_andamento": base.filter(Tarefa.status == StatusTarefa.EM_ANDAMENTO).count(),
            "concluidas": base.filter(Tarefa.status == StatusTarefa.CONCLUIDA).count(),
            "atrasadas": atrasadas,
        })
    return resultado

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

    return query.order_by(Tarefa.data_prazo.asc()).all()

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
            and not db_tarefa.anexo_nome):
        obrig = (db.query(Obrigacao).filter(Obrigacao.id == db_tarefa.obrigacao_id).first()
                 if db_tarefa.obrigacao_id else None)
        if _exige_documento(obrig):
            raise HTTPException(
                status_code=403,
                detail="Esta tarefa exige validação de documento — baixe pelo e-validador. Baixa manual não é permitida.")

    if tarefa.status == StatusTarefa.CONCLUIDA and not db_tarefa.data_conclusao:
        update_data["data_conclusao"] = datetime.utcnow()

    # responsaveis (M2M) tratado à parte
    if "responsavel_ids" in update_data:
        _aplicar_responsaveis(db, db_tarefa, update_data.pop("responsavel_ids"))

    for key, value in update_data.items():
        setattr(db_tarefa, key, value)

    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

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

    db_tarefa.status = StatusTarefa.CANCELADA
    db.commit()
    return {"message": "Tarefa cancelada com sucesso"}
