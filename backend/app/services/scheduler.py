from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..database import SessionLocal
from .whatsapp import check_and_send_alerts
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_check():
    db = SessionLocal()
    try:
        logger.info("Iniciando verificação agendada de tarefas...")
        alerts = await check_and_send_alerts(db)
        logger.info(f"Verificação concluída. {len(alerts)} alertas processados.")
        for alert in alerts:
            logger.info(f"  - {alert['tarefa_titulo']} -> {alert['responsavel']} (enviado: {alert['enviado']})")
    except Exception as e:
        logger.error(f"Erro na verificação agendada: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        scheduled_check,
        CronTrigger(hour=8, minute=0),
        id="check_tarefas_manha",
        name="Verificação matinal de tarefas"
    )
    scheduler.add_job(
        scheduled_check,
        CronTrigger(hour=14, minute=0),
        id="check_tarefas_tarde",
        name="Verificação vespertina de tarefas"
    )
    scheduler.add_job(
        scheduled_check,
        CronTrigger(hour=18, minute=0),
        id="check_tarefas_noite",
        name="Verificação noturna de tarefas"
    )
    scheduler.start()
    logger.info("Scheduler iniciado com 3 verificações diárias (8h, 14h, 18h)")
