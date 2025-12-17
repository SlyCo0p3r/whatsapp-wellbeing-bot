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
import time
import signal
import sys
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

logger = logging.getLogger("whatsapp_bot")

# ================== CONFIG ==================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")

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
# Par défaut, autorise uniquement les requêtes locales pour le widget
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",") if origin.strip()]

# Token pour protéger les endpoints de debug (optionnel, désactive les endpoints si non défini)
DEBUG_TOKEN = os.getenv("DEBUG_TOKEN", None)
ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "false").lower() == "true"

TEMPLATE_DAILY = "mc_daily_ping"
TEMPLATE_ALERT = "mc_safety_alert"
TEMPLATE_OK = "mc_ok"

STATE_FILE = "data/state.json"

app = Flask(__name__)

# Limiter la taille des requêtes pour éviter les attaques DoS (16 MB max)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# CORS sécurisé : uniquement les origines autorisées
if CORS_ORIGINS:
    CORS(app, origins=CORS_ORIGINS)
else:
    # Si aucune origine n'est configurée, désactiver CORS pour la sécurité
    logger.warning("⚠️ CORS_ORIGINS non configuré, CORS désactivé")

# Créer le dossier data s'il n'existe pas
os.makedirs("data", exist_ok=True)

# ================== STATE MANAGER ==================
class StateManager:
    """Gestionnaire d'état thread-safe avec validation et fallback"""
    
    DEFAULT_STATE = {
        "waiting": False,
        "deadline": None,
        "last_reply": None,
        "last_ping": None,
        "alert_sent": False
    }
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.lock = threading.Lock()
        self._state = self._load_state()
    
    def _validate_state(self, state: dict) -> dict:
        """Valide et normalise l'état avec valeurs par défaut"""
        validated = self.DEFAULT_STATE.copy()
        
        # Migration et validation des champs
        if isinstance(state, dict):
            validated["waiting"] = bool(state.get("waiting", False))
            validated["alert_sent"] = bool(state.get("alert_sent", False))
            
            # Validation des dates ISO
            for date_field in ["deadline", "last_reply", "last_ping"]:
                value = state.get(date_field)
                if value is None:
                    validated[date_field] = None
                elif isinstance(value, str):
                    try:
                        # Valider que c'est une date ISO valide
                        datetime.datetime.fromisoformat(value)
                        validated[date_field] = value
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ Date invalide dans state: {date_field}={value}, réinitialisation")
                        validated[date_field] = None
                else:
                    validated[date_field] = None
        
        return validated
    
    def _load_state(self) -> dict:
        """Charge l'état depuis le fichier avec validation et fallback"""
        try:
            if not os.path.exists(self.state_file):
                logger.info("📝 Création d'un nouvel état par défaut")
                return self.DEFAULT_STATE.copy()
            
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # Validation et normalisation
            validated_state = self._validate_state(state)
            
            # Si l'état a été modifié par la validation, le sauvegarder
            if validated_state != state:
                logger.info("🔧 État corrigé et sauvegardé")
                self._save_state_internal(validated_state)
            
            return validated_state
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Fichier state.json corrompu (JSON invalide): {e}")
            logger.info("🔄 Restauration de l'état par défaut")
            # Sauvegarder un backup du fichier corrompu
            try:
                backup_file = f"{self.state_file}.corrupt.{int(time.time())}"
                os.rename(self.state_file, backup_file)
                logger.info(f"💾 Backup du fichier corrompu: {backup_file}")
            except Exception:
                pass
            return self.DEFAULT_STATE.copy()
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture state.json: {e}", exc_info=True)
            return self.DEFAULT_STATE.copy()
    
    def _save_state_internal(self, state: dict):
        """Sauvegarde interne (sans lock, appelée depuis méthodes avec lock)"""
        try:
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Erreur écriture state.json: {e}", exc_info=True)
            raise
    
    def get_state(self) -> dict:
        """Récupère une copie de l'état actuel"""
        with self.lock:
            return self._state.copy()
    
    def update_state(self, updates: dict):
        """Met à jour l'état de manière thread-safe"""
        with self.lock:
            self._state.update(updates)
            self._save_state_internal(self._state)
    
    def reset_waiting(self):
        """Réinitialise l'état d'attente"""
        with self.lock:
            self._state["waiting"] = False
            self._state["deadline"] = None
            self._state["alert_sent"] = False
            self._save_state_internal(self._state)
    
    def set_waiting(self, deadline: datetime.datetime):
        """Définit l'état d'attente avec une deadline"""
        with self.lock:
            now = datetime.datetime.now(tz=TZ)
            self._state["waiting"] = True
            self._state["deadline"] = deadline.isoformat()
            self._state["last_ping"] = now.isoformat()
            self._state["alert_sent"] = False
            self._save_state_internal(self._state)
    
    def set_reply(self):
        """Enregistre une réponse reçue"""
        with self.lock:
            self._state["waiting"] = False
            self._state["deadline"] = None
            self._state["alert_sent"] = False
            self._state["last_reply"] = datetime.datetime.now(tz=TZ).isoformat()
            self._save_state_internal(self._state)
    
    def mark_alert_sent(self):
        """Marque qu'une alerte a été envoyée"""
        with self.lock:
            self._state["alert_sent"] = True
            self._save_state_internal(self._state)

# Instance globale du gestionnaire d'état
state_manager = StateManager(STATE_FILE)

# ================== WHATSAPP SENDERS ==================
def wa_call(payload: dict, retry=2):
    """Appelle l'API WhatsApp avec retry automatique et gestion d'erreurs améliorée"""
    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    for attempt in range(retry):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            
            # Parsing sécurisé du body JSON
            try:
                if r.headers.get("content-type", "").startswith("application/json"):
                    body = r.json()
                else:
                    body = r.text
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"⚠️ Impossible de parser le JSON de la réponse: {e}")
                body = r.text
            
            if r.status_code == 200:
                logger.info("✅ WhatsApp API OK", extra={"body": body})
                return r
            
            # Gestion spécifique des erreurs HTTP
            elif r.status_code == 401:
                logger.error("❌ Token WhatsApp expiré ou invalide (401). Régénérez votre token dans Meta Developer Dashboard.")
                return None  # Ne pas retry pour les erreurs d'authentification
            
            elif r.status_code == 429:
                # Rate limiting - attendre avant de retry
                retry_after = int(r.headers.get("Retry-After", 60))
                logger.warning(f"⚠️ Rate limit atteint (429). Attente de {retry_after}s avant retry...")
                if attempt < retry - 1:  # Pas de sleep sur la dernière tentative
                    time.sleep(retry_after)
                continue
            
            elif r.status_code >= 500:
                # Erreurs serveur - retry avec backoff
                logger.warning(f"⚠️ Erreur serveur WhatsApp {r.status_code}: {body}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)  # Backoff exponentiel: 1s, 2s, 4s...
                continue
            
            else:
                # Autres erreurs (400, 403, etc.) - ne pas retry
                error_code = body.get("error", {}).get("code", "unknown") if isinstance(body, dict) else "unknown"
                error_message = body.get("error", {}).get("message", str(body)) if isinstance(body, dict) else str(body)
                logger.error(f"❌ WhatsApp API erreur {r.status_code} (code: {error_code}): {error_message}")
                return None
                
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Timeout sur tentative {attempt+1}/{retry}: {e}")
            if attempt == retry - 1:
                return None
            time.sleep(2 ** attempt)  # Backoff exponentiel
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Tentative {attempt+1}/{retry} - Erreur réseau: {e}")
            if attempt == retry - 1:  # dernière tentative
                return None
            time.sleep(2 ** attempt)  # Backoff exponentiel
    
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
    try:
        now = datetime.datetime.now(tz=TZ)
        logger.info(f"[PING] envoi du template {TEMPLATE_DAILY} à {OWNER_PHONE}")
        
        result = send_template(OWNER_PHONE, TEMPLATE_DAILY)
        
        if result and result.status_code == 200:
            deadline = now + datetime.timedelta(minutes=RESPONSE_TIMEOUT_MIN)
            state_manager.set_waiting(deadline)
            logger.info(f"⏰ Deadline fixée à {deadline.strftime('%H:%M')}")
        else:
            logger.error("❌ Échec de l'envoi du ping quotidien")
            
    except Exception as e:
        logger.error(f"❌ Erreur dans daily_ping: {e}", exc_info=True)

def check_deadline():
    try:
        state = state_manager.get_state()
        
        if not state.get("waiting"):
            return

        # Vérifier si une alerte a déjà été envoyée pour éviter les doublons
        if state.get("alert_sent", False):
            return

        deadline_iso = state.get("deadline")
        if not deadline_iso:
            return

        try:
            deadline = datetime.datetime.fromisoformat(deadline_iso)
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Deadline invalide dans l'état: {deadline_iso}, réinitialisation")
            state_manager.reset_waiting()
            return

        now = datetime.datetime.now(tz=TZ)

        if now > deadline:
            logger.warning("[ALERTE] ⚠️ Deadline dépassée, envoi aux contacts...")
            
            # Marquer l'alerte comme envoyée AVANT l'envoi pour éviter les doublons
            # même si l'envoi échoue partiellement
            state_manager.mark_alert_sent()
            
            success_count = 0
            for phone in ALERT_PHONES:
                result = send_template(phone, TEMPLATE_ALERT)
                if result and result.status_code == 200:
                    success_count += 1
            
            logger.info(f"✅ Alertes envoyées : {success_count}/{len(ALERT_PHONES)}")
            
            state_manager.reset_waiting()
            
    except Exception as e:
        logger.error(f"❌ Erreur dans check_deadline: {e}", exc_info=True)

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
    try:
        data = request.get_json()
        
        # Validation de la structure JSON
        if not data or not isinstance(data, dict):
            logger.warning("⚠️ Webhook: données JSON invalides ou manquantes")
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        if data.get("object") != "whatsapp_business_account":
            logger.debug(f"ℹ️ Webhook: objet non géré: {data.get('object')}")
            return jsonify({"status": "ok"}), 200

        entries = data.get("entry", [])
        if not isinstance(entries, list) or len(entries) == 0:
            logger.debug("ℹ️ Webhook: aucune entrée trouvée")
            return jsonify({"status": "ok"}), 200

        for entry in entries:
            if not isinstance(entry, dict):
                continue
                
            changes = entry.get("changes", [])
            if not isinstance(changes, list):
                continue
                
            for change in changes:
                if not isinstance(change, dict):
                    continue
                    
                value = change.get("value", {})
                if not isinstance(value, dict):
                    continue
                    
                messages = value.get("messages", [])
                if not isinstance(messages, list):
                    continue
                    
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                        
                    from_number = msg.get("from")
                    if not from_number or not isinstance(from_number, str):
                        continue
                    
                    # Extraction sécurisée du texte
                    text_body = ""
                    text_obj = msg.get("text", {})
                    if isinstance(text_obj, dict):
                        text_body = text_obj.get("body", "").strip().lower()
                    
                    owner_e164 = OWNER_PHONE.replace("+", "")

                    if from_number == owner_e164:
                        logger.info(f"[WEBHOOK] ✅ Réponse du owner: {text_body}")
                        state_manager.set_reply()
                        send_template(OWNER_PHONE, TEMPLATE_OK)
                    else:
                        logger.info(f"[WEBHOOK] ℹ️ Message d'un autre numéro: {from_number}")
                            
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur de parsing JSON dans le webhook: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"❌ Erreur dans le webhook: {e}", exc_info=True)
        
    return jsonify({"status": "ok"}), 200

# ================== HEALTH CHECK ==================
@app.get("/health")
def health():
    """Endpoint pour vérifier que le bot est vivant"""
    state_data = state_manager.get_state()
    return jsonify({
        "status": "ok",
        "waiting": state_data.get("waiting", False),
        "last_ping": state_data.get("last_ping"),
        "last_reply": state_data.get("last_reply")
    }), 200

# ================== DEBUG ENDPOINT ==================
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

@app.get("/debug/ping")
def debug_ping():
    """Force un ping de test (nécessite ENABLE_DEBUG=true et optionnellement DEBUG_TOKEN)"""
    allowed, error_msg = check_debug_access()
    if not allowed:
        return jsonify({"status": "error", "message": error_msg}), 403
    
    daily_ping()
    return jsonify({"status": "ok", "message": "Ping envoyé"}), 200

@app.get("/debug/state")
def debug_state():
    """Voir l'état actuel sans le modifier (nécessite ENABLE_DEBUG=true et optionnellement DEBUG_TOKEN)"""
    allowed, error_msg = check_debug_access()
    if not allowed:
        return jsonify({"status": "error", "message": error_msg}), 403
    
    return jsonify(state_manager.get_state()), 200

# ================== VALIDATION CONFIG ==================
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

# ================== WIDGET ==================
@app.get("/widget")
def widget():
    base_url = request.url_root.rstrip('/')
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-transparent p-2">
    <div id="w" class="max-w-xs bg-gradient-to-br from-purple-600 to-indigo-700 rounded-2xl p-5 text-white shadow-2xl">
        <div class="flex items-center gap-3 mb-4"><div class="text-3xl">🐾</div><div><div class="text-lg font-semibold">Mathieu le Chat</div><div class="text-xs opacity-90">Bot de surveillance</div></div></div>
        <div class="text-center py-5 opacity-80"><div class="inline-block w-6 h-6 border-3 border-white border-t-transparent rounded-full animate-spin mb-2"></div><div class="text-sm">Chargement...</div></div>
    </div>
    <script>
        function f(){{fetch('{base_url}/health').then(r=>r.json()).then(d=>{{var s=d.status!=='ok'?{{t:'offline',l:'Hors ligne',c:'red'}}:d.waiting?{{t:'waiting',l:'En attente',c:'yellow'}}:{{t:'online',l:'Actif',c:'green'}};function fmt(i){{if(!i)return 'Jamais';var m=Math.floor((Date.now()-new Date(i))/60000);if(m<1)return"A l'instant";if(m<60)return'Il y a '+m+'min';if(m<1440)return'Il y a '+Math.floor(m/60)+'h';var dt=new Date(i);return('0'+dt.getDate()).slice(-2)+'/'+('0'+(dt.getMonth()+1)).slice(-2)}}document.getElementById('w').innerHTML='<div class="flex items-center gap-3 mb-4"><div class="text-3xl">🐾</div><div><div class="text-lg font-semibold">Mathieu le Chat</div><div class="text-xs opacity-90">Bot de surveillance</div></div></div><div class="bg-white bg-opacity-20 backdrop-blur-lg rounded-xl p-4 mb-3 space-y-2"><div class="flex justify-between items-center"><span class="text-sm opacity-90">Etat</span><span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-'+s.c+'-500 bg-opacity-30"><span class="w-2 h-2 rounded-full bg-'+s.c+'-500 animate-pulse"></span>'+s.l+'</span></div><div class="flex justify-between items-center"><span class="text-sm opacity-90">Dernier ping</span><span class="text-sm font-semibold">'+fmt(d.last_ping)+'</span></div><div class="flex justify-between items-center"><span class="text-sm opacity-90">Derniere reponse</span><span class="text-sm font-semibold">'+fmt(d.last_reply)+'</span></div></div><div class="text-center text-xs opacity-70">Mise a jour toutes les 30s</div>'}}).catch(()=>{{document.getElementById('w').innerHTML='<div class="flex items-center gap-3 mb-4"><div class="text-3xl">🐾</div><div><div class="text-lg font-semibold">Mathieu le Chat</div><div class="text-xs opacity-90">Bot de surveillance</div></div></div><div class="bg-red-500 bg-opacity-30 rounded-xl p-3 text-center text-sm">⚠️ Erreur de connexion</div>'}})}}f();setInterval(f,30000)
    </script>
</body>
</html>""", 200, {'Content-Type': 'text/html'}

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
