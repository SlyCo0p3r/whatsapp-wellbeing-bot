"""Routes pour les endpoints de debug"""
import logging
from flask import Blueprint, request, jsonify
from config import ENABLE_DEBUG, DEBUG_TOKEN
from scheduler_tasks import daily_ping

logger = logging.getLogger("whatsapp_bot")

# Import de state_manager depuis app.py pour éviter dépendance circulaire
def get_state_manager():
    """Récupère l'instance de state_manager depuis app.py"""
    from app import state_manager
    return state_manager

bp = Blueprint('debug', __name__)


def check_debug_access():
    """Vérifie l'accès aux endpoints de debug"""
    if not ENABLE_DEBUG:
        return False, "Les endpoints de debug sont désactivés. Définissez ENABLE_DEBUG=true pour les activer."
    
    if DEBUG_TOKEN:
        # Vérifier le token dans les headers ou query params
        token = request.headers.get("X-Debug-Token") or request.args.get("token")
        if token != DEBUG_TOKEN:
            return False, "Token de debug invalide ou manquant."
    
    return True, None


@bp.get("/debug/ping")
def debug_ping():
    """Force un ping de test (nécessite ENABLE_DEBUG=true et optionnellement DEBUG_TOKEN)"""
    allowed, error_msg = check_debug_access()
    if not allowed:
        return jsonify({"status": "error", "message": error_msg}), 403
    
    daily_ping()
    return jsonify({"status": "ok", "message": "Ping envoyé"}), 200


@bp.get("/debug/state")
def debug_state():
    """Voir l'état actuel sans le modifier (nécessite ENABLE_DEBUG=true et optionnellement DEBUG_TOKEN)"""
    allowed, error_msg = check_debug_access()
    if not allowed:
        return jsonify({"status": "error", "message": error_msg}), 403
    
    return jsonify(get_state_manager().get_state()), 200

