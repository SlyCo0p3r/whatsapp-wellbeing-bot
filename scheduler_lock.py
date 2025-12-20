"""Verrou inter-process pour éviter de démarrer plusieurs schedulers.

Contexte:
- En production, Gunicorn peut lancer plusieurs workers (processus).
- Si le scheduler APScheduler est démarré à l'import, chaque worker le démarre
  et les jobs (ex: ping quotidien) s'exécutent plusieurs fois.

Cette implémentation utilise un verrou fichier:
- Sur Linux: `fcntl.flock` (recommandé). Le verrou est libéré automatiquement
  quand le processus se termine.
- Sur Windows: tentative via `msvcrt.locking` (best-effort).
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger("whatsapp_bot")


@dataclass
class SchedulerLock:
    path: str
    acquired: bool
    _fh: object | None = None  # file handle conservé ouvert tant que le lock est détenu

    def release(self) -> None:
        """Libère le verrou si détenu (best-effort)."""
        if not self._fh:
            self.acquired = False
            return
        try:
            if os.name == "posix":
                import fcntl  # type: ignore

                try:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                except Exception:
                    # best-effort
                    pass
            elif os.name == "nt":
                import msvcrt  # type: ignore

                try:
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
        finally:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None
            self.acquired = False


def try_acquire_scheduler_lock(lock_path: str) -> SchedulerLock:
    """Tente d'acquérir un verrou non-bloquant. Renvoie un SchedulerLock."""
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)

    # Ouvre (ou crée) le fichier de lock; garder le handle ouvert est essentiel.
    fh = open(lock_path, "a+", encoding="utf-8")

    try:
        if os.name == "posix":
            import fcntl  # type: ignore

            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return SchedulerLock(path=lock_path, acquired=True, _fh=fh)
            except BlockingIOError:
                # Déjà verrouillé par un autre processus
                try:
                    fh.close()
                except Exception:
                    pass
                return SchedulerLock(path=lock_path, acquired=False, _fh=None)
        elif os.name == "nt":
            # Best-effort. Sur Windows, ce projet tourne généralement en conteneur Linux;
            # on garde cette branche pour les exécutions locales.
            import msvcrt  # type: ignore

            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                return SchedulerLock(path=lock_path, acquired=True, _fh=fh)
            except OSError:
                try:
                    fh.close()
                except Exception:
                    pass
                return SchedulerLock(path=lock_path, acquired=False, _fh=None)
        else:
            # Plateforme inconnue: pas de lock, on préfère ne pas démarrer le scheduler.
            logger.warning(f"⚠️ OS non supporté pour le verrou scheduler: {os.name}")
            try:
                fh.close()
            except Exception:
                pass
            return SchedulerLock(path=lock_path, acquired=False, _fh=None)
    except Exception as e:
        # En cas d'erreur inattendue, on évite de démarrer plusieurs schedulers.
        logger.error(f"❌ Impossible d'acquérir le lock scheduler ({lock_path}): {e}", exc_info=True)
        try:
            fh.close()
        except Exception:
            pass
        return SchedulerLock(path=lock_path, acquired=False, _fh=None)


def is_scheduler_lock_held(lock_path: str) -> bool:
    """Indique si un autre processus détient déjà le lock.

    Implémentation:
    - On tente d'acquérir le lock en non-bloquant.
    - Si on y arrive: personne ne le détenait → on relâche immédiatement et on renvoie False.
    - Sinon: le lock est détenu → on renvoie True.
    """
    lock = try_acquire_scheduler_lock(lock_path)
    if lock.acquired:
        lock.release()
        return False
    return True


