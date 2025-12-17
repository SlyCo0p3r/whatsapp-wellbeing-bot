"""Fonctions d'appel à l'API WhatsApp"""
import json
import logging
import time
import requests
from config import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID

logger = logging.getLogger("whatsapp_bot")


def wa_call(payload: dict, retry=2):
    """Appelle l'API WhatsApp avec retry automatique et gestion d'erreurs améliorée"""
    # Vérifier que les tokens sont configurés
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.error("❌ WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID manquant")
        return None
    
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
    """Envoie un template WhatsApp"""
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
    """Envoie un message texte WhatsApp"""
    try:
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
        return wa_call(payload)
    except Exception as e:
        logger.error(f"❌ Impossible d'envoyer le texte à {to}: {e}")
        return None

