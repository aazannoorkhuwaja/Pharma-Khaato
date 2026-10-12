import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from core.path_manager import PathManager
from core.logger import get_logger

logger = get_logger("PharmaKhaatoBackup")


def _validate_sqlite_database(path: str) -> tuple[bool, str]:
    """Validate that a file is an intact SQLite database before trusting it."""
    try:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        # sqlite3.Connection's context manager commits/rolls back but does not
        # close the handle. That distinction matters on Windows, where an open
        # handle prevents the verified .partial file from being renamed.
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            row = conn.execute("PRAGMA quick_check;").fetchone()
        ok = bool(row and str(row[0]).lower() == "ok")
        return ok, "ok" if ok else f"Integrity check returned: {row[0] if row else 'no result'}"
    except (sqlite3.Error, OSError, ValueError) as exc:
        return False, str(exc)


def backup_database():
    """Create an integrity-checked, timestamped online SQLite snapshot."""
    db_path = PathManager.get_db_path()
    if not os.path.exists(db_path):
        return False, "Database file does not exist."

    backup_dir = PathManager.get_backups_dir()
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest_path = os.path.join(backup_dir, f"pharmacy_db_backup_{ts}.sqlite")
    temp_path = dest_path + ".partial"

    try:
        # Explicitly close both handles before integrity checking/renaming.
        # sqlite3's native context manager alone does not close connections.
        with closing(sqlite3.connect(db_path)) as src_conn:
            with closing(sqlite3.connect(temp_path)) as dst_conn:
                src_conn.backup(dst_conn)
                dst_conn.commit()

        valid, reason = _validate_sqlite_database(temp_path)
        if not valid:
            raise sqlite3.DatabaseError(f"Backup integrity check failed: {reason}")

        os.replace(temp_path, dest_path)
        logger.info(f"Database snapshot successfully created: {dest_path}")
        return True, dest_path
    except Exception as exc:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        logger.error(f"Database backup failed: {exc}")
        return False, "Backup could not be created. Check the system details for more information."


def create_db_backup():
    return backup_database()


def list_backups():
    backup_dir = PathManager.get_backups_dir()
    if not os.path.exists(backup_dir):
        return []
    files = []
    for fname in os.listdir(backup_dir):
        if fname.endswith(".sqlite"):
            fpath = os.path.join(backup_dir, fname)
            try:
                st = os.stat(fpath)
            except OSError:
                continue
            files.append({
                "filename": fname,
                "filepath": fpath,
                "size_bytes": st.st_size,
                "created_at": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified_ts": st.st_mtime,
            })
    files.sort(key=lambda item: item["modified_ts"], reverse=True)
    return files


def restore_database(backup_filepath):
    """Restore only from an integrity-checked SQLite snapshot, with a safety copy first."""
    db_path = PathManager.get_db_path()
    if not os.path.exists(backup_filepath):
        return False, "The selected backup file no longer exists."

    valid, reason = _validate_sqlite_database(backup_filepath)
    if not valid:
        logger.warning(f"Rejected invalid backup '{backup_filepath}': {reason}")
        return False, "This backup file is damaged or is not a valid Pharma-Khaato database."

    try:
        from core.db_engine import reset_thread_connections
        reset_thread_connections()

        ok, safety_path = backup_database()
        if not ok:
            return False, "Restore stopped because a safety backup could not be created first."

        with closing(sqlite3.connect(db_path)) as dst_conn:
            with closing(sqlite3.connect(backup_filepath)) as src_conn:
                src_conn.backup(dst_conn)
                dst_conn.commit()

        restored_ok, restored_reason = _validate_sqlite_database(db_path)
        if not restored_ok:
            logger.error(f"Restored DB failed integrity check: {restored_reason}")
            return False, f"Restore failed its integrity check. Safety backup: {safety_path}"

        reset_thread_connections()
        logger.info(f"Database successfully restored from: {backup_filepath}")
        return True, "Backup restored successfully."
    except Exception as exc:
        logger.error(f"Database restore failed: {exc}")
        return False, "Restore could not be completed. Your safety backup was kept."
