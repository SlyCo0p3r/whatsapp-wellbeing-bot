"""Point d'entrée principal du bot WhatsApp Wellbeing"""
import os
import signal
import sys
import logging
from logging_config import configure_logging

# Configurer le logging le plus tôt possible
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    logfile=os.getenv("LOG_FILE", None),
    json=(os.getenv("LOG_JSON", "false").lower() == "true"),
)

from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from config import (
    CORS_ORIGINS, STATE_FILE, TZ, DAILY_HOUR, RESPONSE_TIMEOUT_MIN, ALERT_PHONES,
    validate_config
)
from state_manager import StateManager
from scheduler_tasks import daily_ping, check_deadline
from routes import webhooks, health, debug, widget

logger = logging.getLogger("whatsapp_bot")

# ================== INITIALISATION ==================

# Créer le dossier data s'il n'existe pas
os.makedirs("data", exist_ok=True)

# Instance Flask
app = Flask(__name__)

# Limiter la taille des requêtes pour éviter les attaques DoS (16 MB max)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# CORS sécurisé : uniquement les origines autorisées
if CORS_ORIGINS:
    CORS(app, origins=CORS_ORIGINS)
else:
    logger.warning("⚠️ CORS_ORIGINS non configuré, CORS désactivé")

# Instance globale du gestionnaire d'état
state_manager = StateManager(STATE_FILE)

# ================== SCHEDULER ==================
scheduler = BackgroundScheduler(timezone=str(TZ))
scheduler.add_job(daily_ping, "cron", hour=DAILY_HOUR, minute=0)
scheduler.add_job(check_deadline, "interval", minutes=5)

try:
    scheduler.start()
    logger.info("✅ Scheduler démarré avec succès")
except Exception as e:
    logger.error(f"❌ Échec du démarrage du scheduler: {e}", exc_info=True)
    raise RuntimeError("Impossible de démarrer le scheduler - le bot ne peut pas fonctionner") from e

# Fonction de shutdown propre
def shutdown_handler(signum=None, frame=None):
    """Arrête proprement le scheduler et l'application"""
    logger.info("🛑 Signal d'arrêt reçu, arrêt du scheduler...")
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Scheduler arrêté proprement")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'arrêt du scheduler: {e}")
    sys.exit(0)

# Enregistrer les handlers de signal pour un shutdown propre
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# ================== ROUTES ==================
# Enregistrer les blueprints
app.register_blueprint(webhooks.bp)
app.register_blueprint(health.bp)
app.register_blueprint(debug.bp)
app.register_blueprint(widget.bp)

# ================== MAIN ==================
if __name__ == "__main__":
    validate_config()
    logger.info("🚀 Démarrage du bot WhatsApp Wellbeing")
    logger.info(f"📅 Ping quotidien à {DAILY_HOUR}h")
    logger.info(f"⏱️ Timeout: {RESPONSE_TIMEOUT_MIN} minutes")
    logger.info(f"📞 Contacts d'alerte: {len(ALERT_PHONES)}")
    
    # Détecter si on est en production (Gunicorn) ou développement
    use_gunicorn = os.getenv("USE_GUNICORN", "false").lower() == "true"
    
    if use_gunicorn:
        logger.warning("⚠️ USE_GUNICORN=true détecté, mais lancement avec Flask dev server")
        logger.warning("⚠️ En production, utilisez 'gunicorn app:app' directement ou le Dockerfile")
        logger.info("🔧 Démarrage du serveur Flask de développement...")
    else:
        logger.info("🔧 Mode développement: serveur Flask intégré")
        logger.warning("⚠️ Ne pas utiliser en production! Utilisez Gunicorn avec USE_GUNICORN=true")
    
    # Toujours démarrer Flask, le Dockerfile gère la sélection Gunicorn/Flask
    app.run(host="0.0.0.0", port=5000, debug=False)
