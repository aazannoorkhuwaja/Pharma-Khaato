import os
import logging
from logging.handlers import RotatingFileHandler
from core.path_manager import PathManager

def get_logger(name="PharmaKhaato"):
    """
    Centralized Rotating Logger using PathManager for OS-compliant logging.
    Logs warnings, errors, and audit events to logs/app.log (5MB limit, 3 backups).
    Also emits formatted output to standard console stream.
    """
    log_dir = PathManager.get_logs_dir()
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # 1. Rotating File Handler
        rfh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        rfh.setLevel(logging.INFO)
        file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s")
        rfh.setFormatter(file_fmt)
        logger.addHandler(rfh)

        # 2. Console Stream Handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        console_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        ch.setFormatter(console_fmt)
        logger.addHandler(ch)

    return logger
