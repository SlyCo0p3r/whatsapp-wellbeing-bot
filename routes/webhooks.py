"""Routes pour les webhooks WhatsApp"""
import json
import logging
from flask import Blueprint, request, jsonify
from config import WEBHOOK_VERIFY_TOKEN, OWNER_PHONE, TEMPLATE_OK
from services import get_state_manager
from whatsapp_api import send_template

logger = logging.getLogger("whatsapp_bot")

bp = Blueprint('webhooks', __name__)


@bp.get("/whatsapp/webhook")
def verify():
    """Vérification du webhook par Meta"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        logger.info("✅ Webhook vérifié")
        return challenge, 200
    logger.warning("⚠️ Tentative de vérification webhook échouée")
    return "forbidden", 403


@bp.post("/whatsapp/webhook")
def incoming():
    """Réception des messages WhatsApp depuis Meta"""
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
                    
                    # Vérifier que OWNER_PHONE est configuré
                    if not OWNER_PHONE:
                        logger.warning("⚠️ OWNER_PHONE non configuré, impossible de traiter le message")
                        continue
                    
                    owner_e164 = OWNER_PHONE.replace("+", "")

                    if from_number == owner_e164:
                        logger.info(f"[WEBHOOK] ✅ Réponse du owner: {text_body}")
                        get_state_manager().set_reply()
                        send_template(OWNER_PHONE, TEMPLATE_OK)
                    else:
                        logger.info(f"[WEBHOOK] ℹ️ Message d'un autre numéro: {from_number}")
                            
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur de parsing JSON dans le webhook: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"❌ Erreur dans le webhook: {e}", exc_info=True)
        
    return jsonify({"status": "ok"}), 200

