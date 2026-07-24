from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .whatsapp import check_and_send_alerts
import logging

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Sao_Paulo")
except Exception:  # pragma: no cover
    TZ = None

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_check(slot: str):
    # importa aqui para evitar dependência de import no carregamento do módulo
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        logger.info(f"[{slot}] verificando tarefas...")
        alerts = await check_and_send_alerts(db, slot=slot)
        logger.info(f"[{slot}] {len(alerts)} tarefa(s) notificada(s).")
    except Exception as e:
        logger.error(f"Erro na verificação [{slot}]: {e}")
    finally:
        db.close()


def _cron(hour: int, minute: int) -> CronTrigger:
    if TZ:
        return CronTrigger(hour=hour, minute=minute, timezone=TZ)
    return CronTrigger(hour=hour, minute=minute)


def start_scheduler():
    # Horários em America/Sao_Paulo.
    # Principais (9:30 e 17:45): avisam 3 dias antes, 1 dia antes, no dia e atrasadas.
    scheduler.add_job(scheduled_check, _cron(9, 30), args=["principal"], id="alerta_0930", replace_existing=True)
    scheduler.add_job(scheduled_check, _cron(17, 45), args=["principal"], id="alerta_1745", replace_existing=True)
    # Extras (14:30 e 16:00): avisam só no dia do prazo e atrasadas.
    scheduler.add_job(scheduled_check, _cron(14, 30), args=["extra"], id="alerta_1430", replace_existing=True)
    scheduler.add_job(scheduled_check, _cron(16, 0), args=["extra"], id="alerta_1600", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler iniciado (America/Sao_Paulo): 9:30 e 17:45 (principal); 14:30 e 16:00 (extra).")
