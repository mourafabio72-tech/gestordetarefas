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
    whatsapp_alerts = await check_and_send_alerts(db)
    return {
        "message": f"WhatsApp: {len(whatsapp_alerts)} alertas enviados",
        "whatsapp": whatsapp_alerts
    }


@router.post("/enviar/{usuario_id}")
async def enviar_alerta_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    from ..models import Tarefa, StatusTarefa
    from ..services.whatsapp import send_whatsapp_message, format_task_message, _base_date
    from ..services import config as cfgmod
    from datetime import datetime

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    cfg = cfgmod.carregar(db)
    zap_phone = cfg.get("zap_phone") or ""
    tarefas = db.query(Tarefa).filter(
        Tarefa.responsavel_id == usuario_id,
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
    ).all()

    now = datetime.now()
    results = []

    for tarefa in tarefas:
        base = _base_date(tarefa)
        days_remaining = (base.date() - now.date()).days if base else 0
        message_wa = format_task_message(tarefa, days_remaining, usuario)
        wa_result = await send_whatsapp_message(zap_phone, message_wa, cfg)

        results.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "whatsapp_enviado": wa_result.get("success", False)
        })

    return {
        "message": f"{len(results)} alertas enviados para {usuario.nome}",
        "results": results
    }
