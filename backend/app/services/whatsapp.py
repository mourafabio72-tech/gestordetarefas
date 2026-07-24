import httpx
import os
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Tarefa, Usuario, StatusTarefa

ZAP_API_URL = os.getenv("ZAP_API_URL", "https://api-bps4.zapcontabil.chat")
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "")
ZAP_CONNECTION_FROM = int(os.getenv("ZAP_CONNECTION_FROM", "0"))
ZAP_PHONE = os.getenv("ZAP_PHONE", "5521971985815")  # número central (mesmo para todos)
ALERT_DAYS_BEFORE = int(os.getenv("ALERT_DAYS_BEFORE", "3"))


async def send_whatsapp_message(phone: str, message: str) -> dict:
    if not ZAP_API_KEY:
        return {"success": False, "error": "ZAP_API_KEY não configurada"}

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
            f"{ZAP_API_URL}/api/send/{phone}",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        return {"success": response.status_code == 200, "status_code": response.status_code, "response": response.text}


def _base_date(tarefa: Tarefa):
    """O prazo interno comanda os alertas; se não houver, cai no vencimento."""
    return tarefa.data_prazo or tarefa.data_vencimento


def should_notify(days_remaining: int, slot: str) -> bool:
    """Regras de disparo por proximidade do prazo interno.
    slot 'principal' = 9:30 e 17:45 ; slot 'extra' = 14:30 e 16:00.
      - 3 dias antes e 1 dia antes  -> só nos horários principais
      - no dia do prazo e atrasada  -> em todos os horários
    """
    if days_remaining is None:
        return False
    if days_remaining <= 0:  # vence hoje ou já atrasada -> todos os horários
        return True
    if slot == "principal" and days_remaining in (1, ALERT_DAYS_BEFORE):
        return True
    return False


def format_task_message(tarefa: Tarefa, days_remaining: int, responsavel: Usuario = None) -> str:
    empresa_nome = tarefa.empresa.razao_social or tarefa.empresa.nome_fantasia
    setor_nome = tarefa.setor.nome if tarefa.setor else "Não definido"

    if days_remaining < 0:
        urgency = f"🚨 *ATRASADA há {abs(days_remaining)} dia(s)!*"
    elif days_remaining == 0:
        urgency = "⚠️ *PRAZO INTERNO VENCE HOJE!*"
    elif days_remaining == 1:
        urgency = "⏰ *Prazo interno vence amanhã!*"
    else:
        urgency = f"📋 Prazo interno em *{days_remaining} dias*"

    base = _base_date(tarefa)
    prazo_str = base.strftime("%d/%m/%Y %H:%M") if base else "—"

    linhas = [
        urgency, "",
        f"*Tarefa:* {tarefa.titulo}",
        f"*Empresa:* {empresa_nome}",
        f"*Setor:* {setor_nome}",
        f"*Prazo interno:* {prazo_str}",
    ]
    if tarefa.data_vencimento:
        multa = " ⚠️ *GERA MULTA*" if tarefa.gera_multa else ""
        linhas.append(f"*Vencimento:* {tarefa.data_vencimento.strftime('%d/%m/%Y')}{multa}")
    if responsavel:
        linha = f"*Responsável:* {responsavel.nome}"
        if responsavel.gestor:
            linha += f"  (gestor: {responsavel.gestor.nome})"
        linhas.append(linha)
    linhas.append(f"*Prioridade:* {tarefa.prioridade.value.upper()}")
    linhas += ["", "Por favor, verifique e atualize o status desta tarefa."]
    return "\n".join(linhas)


async def check_and_send_alerts(db: Session, slot: str = "principal") -> list:
    """Varre tarefas em aberto e envia ao número central as que devem ser
    avisadas neste 'slot' de horário."""
    alerts_sent = []
    now = datetime.now()

    tarefas = db.query(Tarefa).filter(
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
    ).all()

    for tarefa in tarefas:
        base = _base_date(tarefa)
        if not base:
            continue

        days_remaining = (base.date() - now.date()).days
        if not should_notify(days_remaining, slot):
            continue

        responsavel = None
        if tarefa.responsavel_id:
            responsavel = db.query(Usuario).filter(Usuario.id == tarefa.responsavel_id).first()

        message = format_task_message(tarefa, days_remaining, responsavel)
        result = await send_whatsapp_message(ZAP_PHONE, message)

        alerts_sent.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "responsavel": responsavel.nome if responsavel else None,
            "dias_restantes": days_remaining,
            "enviado": result.get("success", False),
            "detalhes": result,
        })

    return alerts_sent
