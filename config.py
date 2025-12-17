"""Configuration et validation du bot WhatsApp Wellbeing"""
import os
import logging
import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger("whatsapp_bot")

# ================== CONFIGURATION ==================

# Identifiants WhatsApp
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")

# Numéros de téléphone
OWNER_PHONE = os.getenv("OWNER_PHONE", "").replace(" ", "")
ALERT_PHONES = [p.strip() for p in os.getenv("ALERT_PHONES", "").split(",") if p.strip()]

# Conversion sécurisée des variables numériques avec valeurs par défaut
try:
    DAILY_HOUR = int(os.getenv("DAILY_HOUR", "9"))
except (ValueError, TypeError):
    logger.warning("⚠️ DAILY_HOUR invalide, utilisation de la valeur par défaut: 9")
    DAILY_HOUR = 9

try:
    RESPONSE_TIMEOUT_MIN = int(os.getenv("RESPONSE_TIMEOUT_MIN", "120"))
except (ValueError, TypeError):
    logger.warning("⚠️ RESPONSE_TIMEOUT_MIN invalide, utilisation de la valeur par défaut: 120")
    RESPONSE_TIMEOUT_MIN = 120

# Conversion sécurisée du timezone avec valeur par défaut
try:
    TZ = ZoneInfo(os.getenv("TZ", "Europe/Paris"))
except Exception as e:
    logger.warning(f"⚠️ TZ invalide ({os.getenv('TZ', 'Europe/Paris')}), utilisation de la valeur par défaut: Europe/Paris")
    TZ = ZoneInfo("Europe/Paris")

# CORS: Liste des origines autorisées (séparées par des virgules)
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",") if origin.strip()]

# Debug endpoints
DEBUG_TOKEN = os.getenv("DEBUG_TOKEN", None)
ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "false").lower() == "true"

# Templates WhatsApp
TEMPLATE_DAILY = "mc_daily_ping"
TEMPLATE_ALERT = "mc_safety_alert"
TEMPLATE_OK = "mc_ok"

# Fichier d'état
STATE_FILE = "data/state.json"

# ================== VALIDATION ==================

def validate_config():
    """Vérifie que toutes les variables critiques sont présentes et valides"""
    errors = []
    warnings = []
    
    # Variables obligatoires
    if not WHATSAPP_TOKEN:
        errors.append("❌ WHATSAPP_TOKEN manquant")
    if not WHATSAPP_PHONE_ID:
        errors.append("❌ WHATSAPP_PHONE_ID manquant")
    if not WEBHOOK_VERIFY_TOKEN:
        errors.append("❌ WEBHOOK_VERIFY_TOKEN manquant")
    if not OWNER_PHONE:
        errors.append("❌ OWNER_PHONE manquant")
    if not ALERT_PHONES:
        warnings.append("⚠️ ALERT_PHONES vide (aucun contact d'urgence)")
    
    # Validation des valeurs numériques
    if DAILY_HOUR < 0 or DAILY_HOUR > 23:
        errors.append(f"❌ DAILY_HOUR invalide ({DAILY_HOUR}), doit être entre 0 et 23")
    
    if RESPONSE_TIMEOUT_MIN <= 0:
        errors.append(f"❌ RESPONSE_TIMEOUT_MIN invalide ({RESPONSE_TIMEOUT_MIN}), doit être > 0")
    elif RESPONSE_TIMEOUT_MIN < 5:
        warnings.append(f"⚠️ RESPONSE_TIMEOUT_MIN très court ({RESPONSE_TIMEOUT_MIN} min), recommandé: au moins 30 min")
    
    # Validation du format du numéro de téléphone (basique)
    if OWNER_PHONE and not OWNER_PHONE.startswith("+"):
        warnings.append(f"⚠️ OWNER_PHONE devrait commencer par '+' (format E.164): {OWNER_PHONE}")
    
    # Validation des numéros d'alerte
    for i, phone in enumerate(ALERT_PHONES):
        if phone and not phone.startswith("+"):
            warnings.append(f"⚠️ ALERT_PHONES[{i}] devrait commencer par '+' (format E.164): {phone}")
    
    # Validation du timezone
    try:
        datetime.datetime.now(tz=TZ)
    except Exception as e:
        errors.append(f"❌ TZ invalide ({TZ}): {e}")
    
    # Afficher les warnings
    for warn in warnings:
        logger.warning(warn)
    
    # Afficher les erreurs et lever une exception si nécessaire
    if errors:
        for err in errors:
            logger.error(err)
        raise ValueError("Configuration invalide - vérifiez votre fichier .env")
    
    logger.info("✅ Configuration validée")

