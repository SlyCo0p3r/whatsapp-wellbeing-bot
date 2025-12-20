"""Tâches du scheduler pour le bot WhatsApp Wellbeing"""
import logging
import datetime
from config import TZ, OWNER_PHONE, ALERT_PHONES, RESPONSE_TIMEOUT_MIN, TEMPLATE_DAILY, TEMPLATE_ALERT
from services import get_state_manager
from whatsapp_api import send_template

logger = logging.getLogger("whatsapp_bot")


def daily_ping():
    """Envoie le ping quotidien et définit la deadline"""
    try:
        # Vérifier que OWNER_PHONE est configuré
        if not OWNER_PHONE:
            logger.error("❌ OWNER_PHONE non configuré, impossible d'envoyer le ping")
            return
        
        state_manager = get_state_manager()
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
    """Vérifie si la deadline est dépassée et envoie les alertes si nécessaire"""
    try:
        state_manager = get_state_manager()
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
        
        if now >= deadline:
            logger.warning("[ALERTE] ⚠️ Deadline dépassée, envoi aux contacts...")
            
            # Marquer l'alerte comme envoyée AVANT l'envoi pour éviter les doublons
            # même si l'envoi échoue partiellement
            state_manager.mark_alert_sent()
            
            # Vérifier qu'il y a des contacts d'alerte configurés
            if not ALERT_PHONES:
                logger.warning("⚠️ Aucun contact d'alerte configuré (ALERT_PHONES vide)")
                state_manager.reset_waiting()
                return
            
            success_count = 0
            for phone in ALERT_PHONES:
                result = send_template(phone, TEMPLATE_ALERT)
                if result and result.status_code == 200:
                    success_count += 1
            
            logger.info(f"✅ Alertes envoyées : {success_count}/{len(ALERT_PHONES)}")
            
            state_manager.reset_waiting()
            
    except Exception as e:
        logger.error(f"❌ Erreur dans check_deadline: {e}", exc_info=True)

