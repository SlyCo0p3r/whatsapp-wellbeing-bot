"""Services/singletons partagés.

Objectif:
- Éviter les imports circulaires du type `from app import state_manager`.
- Centraliser l'instanciation des services (StateManager, etc.)
"""

import logging

from config import STATE_FILE
from state_manager import StateManager

logger = logging.getLogger("whatsapp_bot")


# Singleton : un seul StateManager par process.
state_manager = StateManager(STATE_FILE)


def get_state_manager() -> StateManager:
    return state_manager


