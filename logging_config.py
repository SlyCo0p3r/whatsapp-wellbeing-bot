import logging
import sys
from logging.handlers import RotatingFileHandler

try:
    from colorlog import ColoredFormatter
    COLORLOG_AVAILABLE = True
except Exception:
    COLORLOG_AVAILABLE = False

def configure_logging(level: str = "INFO", logfile: str | None = None, max_bytes: int = 10*1024*1024, backup_count: int = 3, json: bool = False):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # remove existing handlers (useful during reloads)
    for h in list(root.handlers):
        root.removeHandler(h)

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(root.level)

    if json:
        try:
            from pythonjsonlogger import jsonlogger
            fmt = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        except Exception:
            fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        if COLORLOG_AVAILABLE:
            fmt = ColoredFormatter("%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        else:
            fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    ch.setFormatter(fmt)
    root.addHandler(ch)

    if logfile:
        fh = RotatingFileHandler(logfile, maxBytes=max_bytes, backupCount=backup_count)
        fh.setLevel(root.level)
        fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        root.addHandler(fh)

    # reduce noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
