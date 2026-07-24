from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..database import SessionLocal
from .whatsapp import check_and_send_alerts
from .teams import send_teams_alerts
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_check():
    db = SessionLocal()
    try:
        logger.info("Iniciando verificação agendada de tarefas...")

        whatsapp_alerts = await check_and_send_alerts(db)
        logger.info(f"WhatsApp: {len(whatsapp_alerts)} alertas processados.")

        teams_alerts = await send_teams_alerts(db)
        logger.info(f"Teams: {len(teams_alerts)} alertas processados.")

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
