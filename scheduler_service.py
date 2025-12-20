"""Gestion du scheduler APScheduler (single-instance via lock fichier).

Pourquoi:
- En production, Gunicorn peut démarrer plusieurs workers (processus).
- Si le scheduler est démarré dans chaque process, les jobs partent en double.

Solution:
- Un verrou fichier (`data/scheduler.lock`) empêche plusieurs processus de démarrer le scheduler.
"""

from __future__ import annotations

import os
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import TZ, DAILY_HOUR
from scheduler_lock import try_acquire_scheduler_lock, is_scheduler_lock_held
from scheduler_tasks import daily_ping, check_deadline

logger = logging.getLogger("whatsapp_bot")


SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
SCHEDULER_LOCK_FILE = os.getenv("SCHEDULER_LOCK_FILE", "data/scheduler.lock")

_scheduler_lock = None

# Scheduler global (par process)
scheduler = BackgroundScheduler(timezone=str(TZ))
scheduler.add_job(daily_ping, "cron", hour=DAILY_HOUR, minute=0)
scheduler.add_job(check_deadline, "interval", minutes=5)


def start_scheduler() -> bool:
    """Démarre le scheduler si activé et si le lock est acquis.

    Retourne True si le scheduler a été effectivement démarré dans ce process.
    """
    global _scheduler_lock

    if not SCHEDULER_ENABLED:
        logger.warning("⚠️ SCHEDULER_ENABLED=false: scheduler désactivé")
        return False

    if scheduler.running:
        return True

    _scheduler_lock = try_acquire_scheduler_lock(SCHEDULER_LOCK_FILE)
    if not _scheduler_lock.acquired:
        logger.warning(
            "⚠️ Scheduler non démarré: un autre processus détient déjà le lock "
            f"({SCHEDULER_LOCK_FILE})."
        )
        return False

    try:
        scheduler.start()
        logger.info("✅ Scheduler démarré (lock acquis)")
        return True
    except Exception as e:
        logger.error(f"❌ Échec du démarrage du scheduler: {e}", exc_info=True)
        try:
            _scheduler_lock.release()
        except Exception:
            pass
        raise


def stop_scheduler() -> None:
    """Arrêt propre du scheduler + libération du lock (best-effort)."""
    global _scheduler_lock

    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Scheduler arrêté proprement")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'arrêt du scheduler: {e}", exc_info=True)

    try:
        if _scheduler_lock and getattr(_scheduler_lock, "acquired", False):
            _scheduler_lock.release()
    except Exception:
        pass
    finally:
        _scheduler_lock = None


def is_scheduler_active() -> bool:
    """Indique si un scheduler est actif (dans ce process ou un autre)."""
    if not SCHEDULER_ENABLED:
        return False
    return is_scheduler_lock_held(SCHEDULER_LOCK_FILE) or bool(scheduler.running)


