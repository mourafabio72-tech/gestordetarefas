from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Usuario
from ..auth import get_current_user
from ..services.whatsapp import check_and_send_alerts

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.post("/verificar")
async def verificar_tarefas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    alerts = await check_and_send_alerts(db)
    return {
        "message": f"{len(alerts)} alertas processados",
        "alerts": alerts
    }


@router.post("/enviar/{usuario_id}")
async def enviar_alerta_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    from ..models import Tarefa, StatusTarefa
    from ..services.whatsapp import send_whatsapp_message, format_task_message
    from datetime import datetime

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not usuario.email:
        raise HTTPException(status_code=400, detail="Usuário não possui email cadastrado")

    tarefas = db.query(Tarefa).filter(
        Tarefa.responsavel_id == usuario_id,
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
    ).all()

    now = datetime.now()
    alerts_sent = []

    for tarefa in tarefas:
        days_remaining = (tarefa.data_prazo.date() - now.date()).days
        message = format_task_message(tarefa, days_remaining)
        result = await send_whatsapp_message(usuario.email, message)
        alerts_sent.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "enviado": result.get("success", False)
        })

    return {
        "message": f"{len(alerts_sent)} alertas enviados para {usuario.nome}",
        "alerts": alerts_sent
    }
