import httpx
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Tarefa, Usuario, StatusTarefa

ZAP_API_URL = os.getenv("ZAP_API_URL", "https://api-bps4.zapcontabil.chat")
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "")
ZAP_CONNECTION_FROM = int(os.getenv("ZAP_CONNECTION_FROM", "0"))
ALERT_DAYS_BEFORE = int(os.getenv("ALERT_DAYS_BEFORE", "3"))


async def send_whatsapp_message(phone: str, message: str) -> dict:
    if not ZAP_API_KEY:
        return {"success": False, "error": "ZAP_API_KEY não configurada"}

    clean_phone = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

    headers = {
        "Authorization": f"Bearer {ZAP_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "body": message,
        "connectionFrom": ZAP_CONNECTION_FROM
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ZAP_API_URL}/api/send/{clean_phone}",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        return {"success": response.status_code == 200, "status_code": response.status_code}


def format_task_message(tarefa: Tarefa, days_remaining: int) -> str:
    empresa_nome = tarefa.empresa.razao_social or tarefa.empresa.nome_fantasia
    setor_nome = tarefa.setor.nome if tarefa.setor else "Não definido"

    if days_remaining < 0:
        urgency = f"🚨 *ATRASADA há {abs(days_remaining)} dia(s)!*"
    elif days_remaining == 0:
        urgency = "⚠️ *VENCE HOJE!*"
    elif days_remaining == 1:
        urgency = "⏰ *Vence amanhã!*"
    else:
        urgency = f"📋 Vence em *{days_remaining} dias*"

    prazo_str = tarefa.data_prazo.strftime("%d/%m/%Y %H:%M")

    message = f"""{urgency}

*Tarefa:* {tarefa.titulo}
*Empresa:* {empresa_nome}
*Setor:* {setor_nome}
*Prazo:* {prazo_str}
*Prioridade:* {tarefa.prioridade.value.upper()}

Por favor, verifique e atualize o status desta tarefa."""

    return message


async def check_and_send_alerts(db: Session) -> list:
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

            if responsavel and responsavel.telefone:
                message = format_task_message(tarefa, days_remaining)
                result = await send_whatsapp_message(responsavel.telefone, message)

                alerts_sent.append({
                    "tarefa_id": tarefa.id,
                    "tarefa_titulo": tarefa.titulo,
                    "responsavel": responsavel.nome,
                    "telefone": responsavel.telefone,
                    "dias_restantes": days_remaining,
                    "enviado": result.get("success", False)
                })

    return alerts_sent
