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
from config import (
    CORS_ORIGINS, TZ, DAILY_HOUR, RESPONSE_TIMEOUT_MIN, ALERT_PHONES,
    validate_config
)
from scheduler_service import start_scheduler, stop_scheduler
from routes import webhooks, health, debug, widget

logger = logging.getLogger("whatsapp_bot")

# ================== INITIALISATION ==================

# Créer le dossier data s'il n'existe pas (state.json + lock scheduler)
os.makedirs("data", exist_ok=True)

# Validation de config au démarrage (Gunicorn inclus): fail-fast en prod.
validate_config()

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
# (StateManager est instancié dans services.py)

# ================== SCHEDULER ==================
start_scheduler()

# Fonction de shutdown propre
def shutdown_handler(signum=None, frame=None):
    """Arrête proprement le scheduler et l'application"""
    logger.info("🛑 Signal d'arrêt reçu, arrêt du scheduler...")
    stop_scheduler()
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
    logger.info("🚀 Démarrage du bot WhatsApp Wellbeing")
    logger.info(f"📅 Ping quotidien à {DAILY_HOUR}h")
    logger.info(f"⏱️ Timeout: {RESPONSE_TIMEOUT_MIN} minutes")
    logger.info(f"📞 Contacts d'alerte: {len(ALERT_PHONES)}")
    
    logger.info("🔧 Démarrage du serveur Flask intégré (développement)")
    logger.warning("⚠️ En production, utilisez Gunicorn (USE_GUNICORN=true via Dockerfile)")
    
    app.run(host="0.0.0.0", port=5000, debug=False)
