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


def _recover_staged_backup(filepath, username, password):
    """Require independent shop trust and a snapshot manager before recovery."""
    with _RECOVERY_GATE:
        state_path = os.path.join(PathManager.get_config_dir(), "recovery-attempts.json")
        try:
            with open(state_path, encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            state = {}
        if float(state.get("locked_until", 0)) > time.time():
            return False, "Too many recovery attempts. Wait one minute and try again."
        from core.backup_trust import verify_snapshot
        if not verify_snapshot(filepath):
            return False, ("This backup cannot be authenticated by this shop's recovery key. "
                           "Use a signed shop backup and its matching owner-held recovery key. "
                           "Unsigned legacy backups require an authenticated administrator restore.")
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


def recover_from_backup(filepath, username, password):
    """Verify and restore one private, stable copy, preventing source swap races."""
    import shutil
    import tempfile
    try:
        with tempfile.TemporaryDirectory(prefix="recovery-", dir=PathManager.get_config_dir()) as folder:
            staged = os.path.join(folder, "snapshot.sqlite")
            shutil.copyfile(filepath, staged)
            if os.path.isfile(str(filepath) + ".hmac"):
                shutil.copyfile(str(filepath) + ".hmac", staged + ".hmac")
            return _recover_staged_backup(staged, username, password)
    except (OSError, ValueError):
        return False, "The recovery snapshot could not be read. Check the backup device and retry."
