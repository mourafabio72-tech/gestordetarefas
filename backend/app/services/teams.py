import httpx
import os
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Tarefa, Usuario, StatusTarefa
from .whatsapp import ALERT_DAYS_BEFORE


async def send_teams_message(webhook_url: str, message: str, title: str = "Gestor de Tarefas") -> dict:
    if not webhook_url:
        return {"success": False, "error": "Webhook URL não configurada"}

    payload = {
        "title": title,
        "text": message,
        "themeColor": "FF6600"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        return {"success": response.status_code == 202, "status_code": response.status_code}


def format_task_message_teams(tarefa: Tarefa, days_remaining: int) -> tuple:
    empresa_nome = tarefa.empresa.razao_social or tarefa.empresa.nome_fantasia
    setor_nome = tarefa.setor.nome if tarefa.setor else "Não definido"

    if days_remaining < 0:
        urgency = f"🚨 **ATRASADA há {abs(days_remaining)} dia(s)!**"
        title = f"⚠️ TAREFA ATRASADA - {tarefa.titulo}"
    elif days_remaining == 0:
        urgency = "⚠️ **VENCE HOJE!**"
        title = f"⏰ TAREFA VENCE HOJE - {tarefa.titulo}"
    elif days_remaining == 1:
        urgency = "⏰ **Vence amanhã!**"
        title = f"📋 TAREFA VENCE AMANHÃ - {tarefa.titulo}"
    else:
        urgency = f"📋 Vence em **{days_remaining} dias**"
        title = f"📋 TAREFA - {tarefa.titulo}"

    prazo_str = tarefa.data_prazo.strftime("%d/%m/%Y %H:%M")

    message = f"""{urgency}

**Tarefa:** {tarefa.titulo}
**Empresa:** {empresa_nome}
**Setor:** {setor_nome}
**Prazo:** {prazo_str}
**Prioridade:** {tarefa.prioridade.value.upper()}

Por favor, verifique e atualize o status desta tarefa."""

    return message, title


async def send_teams_alerts(db: Session) -> list:
    alerts_sent = []
    now = datetime.now()

    tarefas = db.query(Tarefa).filter(
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
        Tarefa.responsavel_id.isnot(None)
    ).all()

    for tarefa in tarefas:
        if not tarefa.data_prazo:
            continue

        days_remaining = (tarefa.data_prazo.date() - now.date()).days

        if days_remaining <= ALERT_DAYS_BEFORE:
            responsavel = db.query(Usuario).filter(Usuario.id == tarefa.responsavel_id).first()

            if responsavel and responsavel.teams_webhook:
                message, title = format_task_message_teams(tarefa, days_remaining)
                result = await send_teams_message(responsavel.teams_webhook, message, title)

                alerts_sent.append({
                    "tarefa_id": tarefa.id,
                    "tarefa_titulo": tarefa.titulo,
                    "responsavel": responsavel.nome,
                    "dias_restantes": days_remaining,
                    "enviado": result.get("success", False),
                    "canal": "teams"
                })

    return alerts_sent
