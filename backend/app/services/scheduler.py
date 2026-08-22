from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .whatsapp import check_and_send_alerts, FAIXAS
import logging

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Sao_Paulo")
except Exception:  # pragma: no cover
    TZ = None

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_check(faixa: str):
    # importa aqui para evitar dependência de import no carregamento do módulo
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        logger.info(f"[{faixa}] verificando tarefas...")
        r = await check_and_send_alerts(db, faixa=faixa)
        logger.info(f"[{faixa}] {len(r['tarefas'])} tarefa(s) em "
                    f"{len(r['mensagens'])} mensagem(ns).")
    except Exception as e:
        logger.error(f"Erro na verificação [{faixa}]: {e}")
    finally:
        db.close()


async def scheduled_gerar():
    """Gera automaticamente as tarefas do mês corrente (dia 1)."""
    from ..database import SessionLocal
    from .gerador import gerar_mes_atual
    db = SessionLocal()
    try:
        r = gerar_mes_atual(db)
        logger.info(f"[gerador] mês {r['mes_entrega']}: {r['criadas']} criada(s), {r['puladas']} já existiam.")
    except Exception as e:
        logger.error(f"Erro no gerador automático: {e}")
    finally:
        db.close()


def _cron(hour: int, minute: int, day=None) -> CronTrigger:
    kw = dict(hour=hour, minute=minute)
    if day is not None:
        kw["day"] = day
    if TZ:
        kw["timezone"] = TZ
    return CronTrigger(**kw)


def _parse_horarios(csv: str):
    saida = []
    for h in (csv or "").split(","):
        h = h.strip()
        if not h:
            continue
        try:
            hh, mm = h.split(":")
            saida.append((int(hh), int(mm)))
        except (ValueError, TypeError):
            continue
    return saida


def _agendar_alertas(cfg: dict):
    """(Re)cria os jobs de alerta: um por horário de cada faixa de urgência."""
    for job in scheduler.get_jobs():
        if job.id.startswith("alerta_"):
            scheduler.remove_job(job.id)
    for faixa in FAIXAS:
        for hh, mm in _parse_horarios(cfg.get(f"horarios_{faixa}", "")):
            scheduler.add_job(scheduled_check, _cron(hh, mm), args=[faixa],
                              id=f"alerta_{faixa}_{hh:02d}{mm:02d}", replace_existing=True)


def _cfg():
    from ..database import SessionLocal
    from . import config as cfgmod
    db = SessionLocal()
    try:
        return cfgmod.carregar(db)
    finally:
        db.close()


def reconfigurar_alertas(db=None):
    """Reagenda os alertas com os horários atuais da config (chamado ao salvar)."""
    from . import config as cfgmod
    cfg = cfgmod.carregar(db) if db is not None else _cfg()
    _agendar_alertas(cfg)
    logger.info("Alertas reagendados: " + " | ".join(
        f"{f}={cfg.get('horarios_' + f)}" for f in FAIXAS))


def start_scheduler():
    _agendar_alertas(_cfg())
    # Geração automática das tarefas do mês: todo dia 1 às 6:00.
    scheduler.add_job(scheduled_gerar, _cron(6, 0, day=1), id="gerar_mensal", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler iniciado (horários de alerta vêm da Configuração; gerador dia 1 às 6:00).")
