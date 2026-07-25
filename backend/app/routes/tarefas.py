from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel
from ..database import get_db
from ..models import Tarefa, Empresa, Setor, Usuario, StatusTarefa
from ..schemas import TarefaCreate, TarefaUpdate, TarefaResponse
from ..auth import get_current_user, require_gestor_ou_admin

router = APIRouter(prefix="/tarefas", tags=["tarefas"])


class TransferirRequest(BaseModel):
    responsavel_id: int

@router.get("/dashboard/stats")
def get_dashboard_stats(
    empresa_id: int = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)

    query = db.query(Tarefa)
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

@router.get("", response_model=List[TarefaResponse])
def list_tarefas(
    empresa_id: int = None,
    setor_id: int = None,
    responsavel_id: int = None,
    status: StatusTarefa = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    query = db.query(Tarefa)

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
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return tarefa

@router.post("", response_model=TarefaResponse, status_code=201)
def create_tarefa(
    tarefa: TarefaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    empresa = db.query(Empresa).filter(Empresa.id == tarefa.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if tarefa.setor_id:
        setor = db.query(Setor).filter(Setor.id == tarefa.setor_id).first()
        if not setor:
            raise HTTPException(status_code=404, detail="Setor não encontrado")

    if tarefa.responsavel_id:
        resp = db.query(Usuario).filter(Usuario.id == tarefa.responsavel_id).first()
        if not resp:
            raise HTTPException(status_code=404, detail="Responsável não encontrado")

    db_tarefa = Tarefa(**tarefa.model_dump())
    db.add(db_tarefa)
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

@router.put("/{tarefa_id}", response_model=TarefaResponse)
def update_tarefa(
    tarefa_id: int,
    tarefa: TarefaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not db_tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    update_data = tarefa.model_dump(exclude_unset=True)

    if tarefa.status == StatusTarefa.CONCLUIDA and not db_tarefa.data_conclusao:
        update_data["data_conclusao"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(db_tarefa, key, value)

    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

@router.post("/{tarefa_id}/transferir", response_model=TarefaResponse)
def transferir_tarefa(
    tarefa_id: int,
    body: TransferirRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    db_tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not db_tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    novo_resp = db.query(Usuario).filter(Usuario.id == body.responsavel_id, Usuario.ativo == True).first()
    if not novo_resp:
        raise HTTPException(status_code=404, detail="Novo responsável não encontrado")

    db_tarefa.responsavel_id = body.responsavel_id
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa


@router.delete("/{tarefa_id}")
def delete_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    db_tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not db_tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    db_tarefa.status = StatusTarefa.CANCELADA
    db.commit()
    return {"message": "Tarefa cancelada com sucesso"}
