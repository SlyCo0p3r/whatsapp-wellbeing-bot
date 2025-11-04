import os
import json
import datetime
import threading
import requests
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

# ================== CONFIG ==================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "margdadan-verify")

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
    if not os.path.exists(STATE_FILE):
        return {"waiting": False, "deadline": None, "last_reply": None, "last_ping": None}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with LOCK:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

state = load_state()

# ================== WHATSAPP SENDERS ==================
def wa_call(payload: dict):
    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    try:
        body = r.json()
    except Exception:
        body = r.text
    print("[WA]", r.status_code, body)
    return r

def send_template(to: str, template_name: str, lang_code: str = "fr"):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {"name": template_name, "language": {"code": lang_code}},
    }
    return wa_call(payload)

def send_text(to: str, text: str):
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    return wa_call(payload)

# ================== SCHEDULER TASKS ==================
def daily_ping():
    global state
    now = datetime.datetime.now(tz=TZ)
    print("[PING] envoi du template", TEMPLATE_DAILY, "à", OWNER_PHONE)
    send_template(OWNER_PHONE, TEMPLATE_DAILY)

    deadline = now + datetime.timedelta(minutes=RESPONSE_TIMEOUT_MIN)
    state["waiting"] = True
    state["deadline"] = deadline.isoformat()
    state["last_ping"] = now.isoformat()
    save_state(state)

def check_deadline():
    global state
    state = load_state()
    if not state.get("waiting"):
        return

    deadline_iso = state.get("deadline")
    if not deadline_iso:
        return

    deadline = datetime.datetime.fromisoformat(deadline_iso)
    now = datetime.datetime.now(tz=TZ)

    if now > deadline:
        print("[ALERTE] deadline dépassée, envoi aux contacts...")
        for phone in ALERT_PHONES:
            send_template(phone, TEMPLATE_ALERT)
        state["waiting"] = False
        state["deadline"] = None
        save_state(state)

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
        return challenge, 200
    return "forbidden", 403

@app.post("/whatsapp/webhook")
def incoming():
    global state
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
                        print("[WEBHOOK] réponse du owner:", text_body)
                        state = load_state()
                        state["waiting"] = False
                        state["deadline"] = None
                        state["last_reply"] = datetime.datetime.now(tz=TZ).isoformat()
                        save_state(state)
                        send_template(OWNER_PHONE, TEMPLATE_OK)
                    else:
                        print("[WEBHOOK] message reçu d’un autre numéro:", from_number)
    return jsonify({"status": "ok"}), 200

# ================== DEBUG ENDPOINT ==================
@app.get("/debug/ping")
def debug_ping():
    daily_ping()
    return "ok", 200

# ================== MAIN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
