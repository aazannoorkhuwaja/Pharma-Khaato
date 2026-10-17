"""Recovery authentication that does not open or modify the damaged live DB."""

import json
import os
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

from core.auth_service import _verify_password
from core.backup_service import _validate_sqlite_database, restore_database
from core.logger import get_logger
from core.path_manager import PathManager

_RECOVERY_GATE = threading.Lock()
logger = get_logger("PharmaKhaatoRecovery")


def recover_from_backup(filepath, username, password):
    """Require a manager from the selected snapshot before pre-login recovery."""
    with _RECOVERY_GATE:
        state_path = os.path.join(PathManager.get_config_dir(), "recovery-attempts.json")
        try:
            with open(state_path, encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            state = {}
        if float(state.get("locked_until", 0)) > time.time():
            return False, "Too many recovery attempts. Wait one minute and try again."
        valid, reason = _validate_sqlite_database(filepath)
        if not valid:
            return False, "Choose a valid Pharma Khaato backup. " + reason
        try:
            uri = Path(filepath).resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as conn:
                row = conn.execute("SELECT password, occupation FROM Employee WHERE username=?", (str(username).strip(),)).fetchone()
            authenticated = bool(row and str(row[1]).lower() in {"admin", "administrator", "manager"}
                                 and _verify_password(password, row[0]))
        except (sqlite3.Error, OSError):
            authenticated = False
        if not authenticated:
            attempts = int(state.get("attempts", 0)) + 1
            state = {"attempts": attempts, "locked_until": time.time() + 60 if attempts >= 5 else 0}
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(state, handle)
            logger.warning("Pre-login recovery authentication failed.")
            return False, "Use an administrator or manager account that existed when this backup was made."
        try:
            os.remove(state_path)
        except FileNotFoundError:
            pass
        logger.info("Pre-login recovery authorized by a snapshot administrator/manager.")
        return restore_database(filepath, require_restart=True)
