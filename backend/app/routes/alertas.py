from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Usuario
from ..auth import get_current_user
from ..services.whatsapp import check_and_send_alerts
from ..services.teams import send_teams_alerts, send_teams_message

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.post("/verificar")
async def verificar_tarefas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    whatsapp_alerts = await check_and_send_alerts(db)
    teams_alerts = await send_teams_alerts(db)

    return {
        "message": f"WhatsApp: {len(whatsapp_alerts)} alertas | Teams: {len(teams_alerts)} alertas",
        "whatsapp": whatsapp_alerts,
        "teams": teams_alerts
    }


@router.post("/enviar/{usuario_id}")
async def enviar_alerta_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    from ..models import Tarefa, StatusTarefa
    from ..services.whatsapp import send_whatsapp_message, format_task_message, ZAP_PHONE
    from datetime import datetime

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    tarefas = db.query(Tarefa).filter(
        Tarefa.responsavel_id == usuario_id,
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
    ).all()

    now = datetime.now()
    results = []

    for tarefa in tarefas:
        days_remaining = (tarefa.data_prazo.date() - now.date()).days

        message_wa, _ = format_task_message(tarefa, days_remaining)
        wa_result = await send_whatsapp_message(ZAP_PHONE, message_wa)

        teams_result = {"success": False, "error": "Webhook não configurado"}
        if usuario.teams_webhook:
            from ..services.teams import format_task_message_teams
            message_teams, title_teams = format_task_message_teams(tarefa, days_remaining)
            teams_result = await send_teams_message(usuario.teams_webhook, message_teams, title_teams)

        results.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "whatsapp_enviado": wa_result.get("success", False),
            "teams_enviado": teams_result.get("success", False)
        })

    return {
        "message": f"{len(results)} alertas enviados para {usuario.nome}",
        "results": results
    }


@router.post("/testar-teams")
async def testar_teams(
    current_user: Usuario = Depends(get_current_user)
):
    if not current_user.teams_webhook:
        raise HTTPException(status_code=400, detail="Configure sua webhook URL do Teams primeiro")

    result = await send_teams_message(
        current_user.teams_webhook,
        "✅ Teste de integração do Gestor de Tarefas com Microsoft Teams!",
        "Teste Gestor de Tarefas"
    )
    return {"message": "Teste enviado", "success": result.get("success", False), "details": result}
