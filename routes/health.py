"""Routes pour health check et statistiques"""
import datetime
import logging
from flask import Blueprint, jsonify
from config import TZ, DAILY_HOUR, RESPONSE_TIMEOUT_MIN, ALERT_PHONES
from scheduler_lock import is_scheduler_lock_held

logger = logging.getLogger("whatsapp_bot")

# Import de state_manager depuis app.py pour éviter dépendance circulaire
def get_state_manager():
    """Récupère l'instance de state_manager depuis app.py"""
    from app import state_manager
    return state_manager

bp = Blueprint('health', __name__)


@bp.get("/health")
def health():
    """Endpoint pour vérifier que le bot est vivant"""
    state_data = get_state_manager().get_state()
    return jsonify({
        "status": "ok",
        "waiting": state_data.get("waiting", False),
        "last_ping": state_data.get("last_ping"),
        "last_reply": state_data.get("last_reply")
    }), 200


@bp.get("/stats")
def stats():
    """Retourne les statistiques d'utilisation du bot"""
    state_data = get_state_manager().get_state()
    stats_data = state_data.get("stats", {})
    
    # Calculer le taux de réponse
    total_pings = stats_data.get("total_pings", 0)
    total_replies = stats_data.get("total_replies", 0)
    response_rate = (total_replies / total_pings * 100) if total_pings > 0 else 0
    
    # Calculer l'uptime (depuis le premier ping)
    uptime_days = None
    first_ping_date = stats_data.get("first_ping_date")
    if first_ping_date:
        try:
            first_ping = datetime.datetime.fromisoformat(first_ping_date)
            now = datetime.datetime.now(tz=TZ)
            uptime_days = (now - first_ping).days
        except (ValueError, TypeError):
            pass
    
    # État du scheduler (importé depuis app.py pour éviter dépendance circulaire)
    try:
        from app import scheduler, SCHEDULER_ENABLED, SCHEDULER_LOCK_FILE
        # Avec Gunicorn multi-workers, le scheduler ne tourne que dans 1 process.
        # Cette vérification via lock reflète mieux "est-ce qu'il y a un scheduler actif quelque part ?"
        scheduler_running = bool(SCHEDULER_ENABLED) and (
            is_scheduler_lock_held(SCHEDULER_LOCK_FILE) or (scheduler.running if scheduler else False)
        )
    except (ImportError, AttributeError):
        scheduler_running = False
    
    return jsonify({
        "status": "ok",
        "stats": {
            "total_pings": total_pings,
            "total_alerts": stats_data.get("total_alerts", 0),
            "total_replies": total_replies,
            "response_rate": round(response_rate, 2),
            "first_ping_date": first_ping_date,
            "uptime_days": uptime_days
        },
        "current_state": {
            "waiting": state_data.get("waiting", False),
            "last_ping": state_data.get("last_ping"),
            "last_reply": state_data.get("last_reply"),
            "scheduler_running": scheduler_running
        },
        "configuration": {
            "daily_hour": DAILY_HOUR,
            "response_timeout_min": RESPONSE_TIMEOUT_MIN,
            "timezone": str(TZ),
            "alert_phones_count": len(ALERT_PHONES)
        }
    }), 200

