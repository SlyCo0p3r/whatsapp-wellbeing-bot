import os
from logging_config import configure_logging

# configure logging as early as possible
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    logfile=os.getenv("LOG_FILE", None),
    json=(os.getenv("LOG_JSON", "false").lower() == "true"),
)

import logging
import json
import datetime
import threading
import requests
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

logger = logging.getLogger("whatsapp_bot")

# ================== CONFIG ==================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")

OWNER_PHONE = os.getenv("OWNER_PHONE", "").replace(" ", "")
ALERT_PHONES = [p.strip() for p in os.getenv("ALERT_PHONES", "").split(",") if p.strip()]

DAILY_HOUR = int(os.getenv("DAILY_HOUR", "9"))
RESPONSE_TIMEOUT_MIN = int(os.getenv("RESPONSE_TIMEOUT_MIN", "120"))
TZ = ZoneInfo(os.getenv("TZ", "Europe/Paris"))

TEMPLATE_DAILY = "mc_daily_ping"
TEMPLATE_ALERT = "mc_safety_alert"
TEMPLATE_OK = "mc_ok"

STATE_FILE = "state.json"
LOCK = threading.Lock()

app = Flask(__name__)

# ================== STATE HELPERS ==================
def load_state():
    try:
        if not os.path.exists(STATE_FILE):
            return {"waiting": False, "deadline": None, "last_reply": None, "last_ping": None}
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur lecture state.json: {e}")
        return {"waiting": False, "deadline": None, "last_reply": None, "last_ping": None}

def save_state(state):
    with LOCK:
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Erreur écriture state.json: {e}")

state = load_state()

# ================== WHATSAPP SENDERS ==================
def wa_call(payload: dict, retry=2):
    """Appelle l'API WhatsApp avec retry automatique"""
    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    for attempt in range(retry):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
            
            if r.status_code == 200:
                logger.info("✅ WhatsApp API OK", extra={"body": body})
                return r
            else:
                logger.warning(f"⚠️ WhatsApp API erreur {r.status_code}: {body}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Tentative {attempt+1}/{retry} - Erreur réseau: {e}")
            if attempt == retry - 1:  # dernière tentative
                raise
    
    return None

def send_template(to: str, template_name: str, lang_code: str = "fr"):
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {"name": template_name, "language": {"code": lang_code}},
        }
        return wa_call(payload)
    except Exception as e:
        logger.error(f"❌ Impossible d'envoyer le template {template_name} à {to}: {e}")
        return None

def send_text(to: str, text: str):
    try:
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
        return wa_call(payload)
    except Exception as e:
        logger.error(f"❌ Impossible d'envoyer le texte à {to}: {e}")
        return None

# ================== SCHEDULER TASKS ==================
def daily_ping():
    global state
    try:
        now = datetime.datetime.now(tz=TZ)
        logger.info(f"[PING] envoi du template {TEMPLATE_DAILY} à {OWNER_PHONE}")
        
        result = send_template(OWNER_PHONE, TEMPLATE_DAILY)
        
        if result and result.status_code == 200:
            deadline = now + datetime.timedelta(minutes=RESPONSE_TIMEOUT_MIN)
            state["waiting"] = True
            state["deadline"] = deadline.isoformat()
            state["last_ping"] = now.isoformat()
            save_state(state)
            logger.info(f"⏰ Deadline fixée à {deadline.strftime('%H:%M')}")
        else:
            logger.error("❌ Échec de l'envoi du ping quotidien")
            
    except Exception as e:
        logger.error(f"❌ Erreur dans daily_ping: {e}")

def check_deadline():
    global state
    try:
        state = load_state()
        if not state.get("waiting"):
            return

        deadline_iso = state.get("deadline")
        if not deadline_iso:
            return

        deadline = datetime.datetime.fromisoformat(deadline_iso)
        now = datetime.datetime.now(tz=TZ)

        if now > deadline:
            logger.warning("[ALERTE] ⚠️ Deadline dépassée, envoi aux contacts...")
            
            success_count = 0
            for phone in ALERT_PHONES:
                result = send_template(phone, TEMPLATE_ALERT)
                if result and result.status_code == 200:
                    success_count += 1
            
            logger.info(f"✅ Alertes envoyées : {success_count}/{len(ALERT_PHONES)}")
            
            state["waiting"] = False
            state["deadline"] = None
            save_state(state)
            
    except Exception as e:
        logger.error(f"❌ Erreur dans check_deadline: {e}")

# ================== SCHEDULER ==================
scheduler = BackgroundScheduler(timezone=str(TZ))
scheduler.add_job(daily_ping, "cron", hour=DAILY_HOUR, minute=0)
scheduler.add_job(check_deadline, "interval", minutes=5)
scheduler.start()

# ================== WEBHOOKS ==================
@app.get("/whatsapp/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        logger.info("✅ Webhook vérifié")
        return challenge, 200
    logger.warning("⚠️ Tentative de vérification webhook échouée")
    return "forbidden", 403

@app.post("/whatsapp/webhook")
def incoming():
    global state
    try:
        data = request.get_json()

        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for msg in messages:
                        from_number = msg.get("from")
                        text_body = msg.get("text", {}).get("body", "").strip().lower()
                        owner_e164 = OWNER_PHONE.replace("+", "")

                        if from_number == owner_e164:
                            logger.info(f"[WEBHOOK] ✅ Réponse du owner: {text_body}")
                            state = load_state()
                            state["waiting"] = False
                            state["deadline"] = None
                            state["last_reply"] = datetime.datetime.now(tz=TZ).isoformat()
                            save_state(state)
                            send_template(OWNER_PHONE, TEMPLATE_OK)
                        else:
                            logger.info(f"[WEBHOOK] ℹ️ Message d'un autre numéro: {from_number}")
                            
    except Exception as e:
        logger.error(f"❌ Erreur dans le webhook: {e}")
        
    return jsonify({"status": "ok"}), 200

# ================== HEALTH CHECK ==================
@app.get("/health")
def health():
    """Endpoint pour vérifier que le bot est vivant"""
    state_data = load_state()
    return jsonify({
        "status": "ok",
        "waiting": state_data.get("waiting", False),
        "last_ping": state_data.get("last_ping"),
        "last_reply": state_data.get("last_reply")
    }), 200

# ================== DEBUG ENDPOINT ==================
@app.get("/debug/ping")
def debug_ping():
    daily_ping()
    return "ok", 200

@app.get("/debug/state")
def debug_state():
    """Voir l'état actuel sans le modifier"""
    return jsonify(load_state()), 200

# ================== VALIDATION CONFIG ==================
def validate_config():
    """Vérifie que toutes les variables critiques sont présentes"""
    errors = []
    
    if not WHATSAPP_TOKEN:
        errors.append("❌ WHATSAPP_TOKEN manquant")
    if not WHATSAPP_PHONE_ID:
        errors.append("❌ WHATSAPP_PHONE_ID manquant")
    if not WEBHOOK_VERIFY_TOKEN:
        errors.append("❌ WEBHOOK_VERIFY_TOKEN manquant")
    if not OWNER_PHONE:
        errors.append("❌ OWNER_PHONE manquant")
    if not ALERT_PHONES:
        errors.append("⚠️ ALERT_PHONES vide (aucun contact d'urgence)")
    
    if errors:
        for err in errors:
            logger.error(err)
        raise ValueError("Configuration invalide - vérifiez votre fichier .env")
    
    logger.info("✅ Configuration validée")

# ================== MAIN ==================
if __name__ == "__main__":
    validate_config()
    logger.info("🚀 Démarrage du bot WhatsApp Wellbeing")
    logger.info(f"📅 Ping quotidien à {DAILY_HOUR}h")
    logger.info(f"⏱️ Timeout: {RESPONSE_TIMEOUT_MIN} minutes")
    logger.info(f"📞 Contacts d'alerte: {len(ALERT_PHONES)}")
    app.run(host="0.0.0.0", port=5000)
