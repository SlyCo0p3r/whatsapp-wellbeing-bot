"""Gestionnaire d'état thread-safe pour le bot WhatsApp Wellbeing"""
import os
import json
import logging
import threading
import time
import datetime
import tempfile
import copy
from zoneinfo import ZoneInfo
from config import TZ, STATE_FILE

logger = logging.getLogger("whatsapp_bot")


class StateManager:
    """Gestionnaire d'état thread-safe avec validation et fallback"""
    
    DEFAULT_STATE = {
        "waiting": False,
        "deadline": None,
        "last_reply": None,
        "last_ping": None,
        "alert_sent": False,
        # Statistiques
        "stats": {
            "total_pings": 0,
            "total_alerts": 0,
            "total_replies": 0,
            "first_ping_date": None
        }
    }
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.lock = threading.Lock()
        self._state = self._load_state()
    
    def _validate_state(self, state: dict) -> dict:
        """Valide et normalise l'état avec valeurs par défaut"""
        # deepcopy pour éviter des références partagées (dict stats)
        validated = copy.deepcopy(self.DEFAULT_STATE)
        
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
            
            # Migration et validation des statistiques
            if "stats" in state and isinstance(state["stats"], dict):
                validated["stats"] = self.DEFAULT_STATE["stats"].copy()
                validated["stats"]["total_pings"] = max(0, int(state["stats"].get("total_pings", 0)))
                validated["stats"]["total_alerts"] = max(0, int(state["stats"].get("total_alerts", 0)))
                validated["stats"]["total_replies"] = max(0, int(state["stats"].get("total_replies", 0)))
                first_ping = state["stats"].get("first_ping_date")
                if first_ping:
                    try:
                        datetime.datetime.fromisoformat(first_ping)
                        validated["stats"]["first_ping_date"] = first_ping
                    except (ValueError, TypeError):
                        validated["stats"]["first_ping_date"] = None
        
        return validated
    
    def _load_state(self) -> dict:
        """Charge l'état depuis le fichier avec validation et fallback"""
        try:
            if not os.path.exists(self.state_file):
                logger.info("📝 Création d'un nouvel état par défaut")
                return copy.deepcopy(self.DEFAULT_STATE)
            
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
            return copy.deepcopy(self.DEFAULT_STATE)
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture state.json: {e}", exc_info=True)
            return copy.deepcopy(self.DEFAULT_STATE)
    
    def _save_state_internal(self, state: dict):
        """Sauvegarde interne (sans lock, appelée depuis méthodes avec lock)"""
        try:
            # Créer le dossier si nécessaire
            state_dir = os.path.dirname(self.state_file)
            if state_dir:  # Si le fichier est dans un sous-dossier
                os.makedirs(state_dir, exist_ok=True)

            # Écriture atomique (NAS-friendly): tmp -> fsync -> os.replace
            tmp_dir = state_dir or "."
            fd, tmp_path = tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=tmp_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        # best-effort (certains FS / environnements)
                        pass

                os.replace(tmp_path, self.state_file)
            finally:
                # Si os.replace a échoué, nettoyer le tmp
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"❌ Erreur écriture state.json: {e}", exc_info=True)
            raise
    
    def get_state(self) -> dict:
        """Récupère une copie de l'état actuel"""
        with self.lock:
            return copy.deepcopy(self._state)
    
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
            
            # Mise à jour des statistiques
            if "stats" not in self._state:
                self._state["stats"] = self.DEFAULT_STATE["stats"].copy()
            self._state["stats"]["total_pings"] = self._state["stats"].get("total_pings", 0) + 1
            if not self._state["stats"].get("first_ping_date"):
                self._state["stats"]["first_ping_date"] = now.isoformat()
            
            self._save_state_internal(self._state)
    
    def set_reply(self):
        """Enregistre une réponse reçue"""
        with self.lock:
            self._state["waiting"] = False
            self._state["deadline"] = None
            self._state["alert_sent"] = False
            self._state["last_reply"] = datetime.datetime.now(tz=TZ).isoformat()
            
            # Mise à jour des statistiques
            if "stats" not in self._state:
                self._state["stats"] = self.DEFAULT_STATE["stats"].copy()
            self._state["stats"]["total_replies"] = self._state["stats"].get("total_replies", 0) + 1
            
            self._save_state_internal(self._state)
    
    def mark_alert_sent(self):
        """Marque qu'une alerte a été envoyée"""
        with self.lock:
            self._state["alert_sent"] = True
            
            # Mise à jour des statistiques
            if "stats" not in self._state:
                self._state["stats"] = self.DEFAULT_STATE["stats"].copy()
            self._state["stats"]["total_alerts"] = self._state["stats"].get("total_alerts", 0) + 1
            
            self._save_state_internal(self._state)
