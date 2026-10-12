import os
import sqlite3
from contextlib import closing
from datetime import datetime, date
from pathlib import Path

from core.path_manager import PathManager
from core.logger import get_logger

logger = get_logger("PharmaKhaatoBackup")
AUTO_BACKUP_PREFIX = "auto_pharmacy_db_backup"


def _validate_sqlite_database(path: str) -> tuple[bool, str]:
    """Validate that a file is an intact SQLite database before trusting it."""
    try:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            row = conn.execute("PRAGMA quick_check;").fetchone()
        ok = bool(row and str(row[0]).lower() == "ok")
        return ok, "ok" if ok else f"Integrity check returned: {row[0] if row else 'no result'}"
    except (sqlite3.Error, OSError, ValueError) as exc:
        return False, str(exc)


def backup_database(prefix="pharmacy_db_backup"):
    """Create an integrity-checked, timestamped online SQLite snapshot."""
    db_path = PathManager.get_db_path()
    if not os.path.exists(db_path):
        return False, "Database file does not exist."

    safe_prefix = "".join(ch for ch in str(prefix) if ch.isalnum() or ch in "_-") or "pharmacy_db_backup"
    backup_dir = PathManager.get_backups_dir()
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest_path = os.path.join(backup_dir, f"{safe_prefix}_{ts}.sqlite")
    temp_path = dest_path + ".partial"

    try:
        with closing(sqlite3.connect(db_path)) as src_conn:
            with closing(sqlite3.connect(temp_path)) as dst_conn:
                src_conn.backup(dst_conn)
                dst_conn.commit()

        valid, reason = _validate_sqlite_database(temp_path)
        if not valid:
            raise sqlite3.DatabaseError(f"Backup integrity check failed: {reason}")

        os.replace(temp_path, dest_path)
        logger.info("Database snapshot successfully created: %s", dest_path)
        return True, dest_path
    except Exception as exc:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        logger.error("Database backup failed: %s", exc)
        return False, "Backup could not be created. Check the system details for more information."


def ensure_daily_backup(retention=14):
    """Create at most one automatic backup per local day and prune old autos.

    Manual backups and pre-migration safety backups are never removed here.
    """
    try:
        retention = max(3, min(int(retention), 90))
    except (TypeError, ValueError):
        retention = 14

    backup_dir = PathManager.get_backups_dir()
    os.makedirs(backup_dir, exist_ok=True)
    today = date.today()

    autos = []
    for name in os.listdir(backup_dir):
        if not (name.startswith(AUTO_BACKUP_PREFIX + "_") and name.endswith(".sqlite")):
            continue
        path = os.path.join(backup_dir, name)
        try:
            stat = os.stat(path)
        except OSError:
            continue
        autos.append((stat.st_mtime, path))
        if datetime.fromtimestamp(stat.st_mtime).date() == today:
            valid, _reason = _validate_sqlite_database(path)
            if valid:
                return True, path

    ok, result = backup_database(AUTO_BACKUP_PREFIX)
    if not ok:
        return False, result

    autos.append((os.path.getmtime(result), result))
    autos.sort(reverse=True)
    for _mtime, old_path in autos[retention:]:
        try:
            os.remove(old_path)
        except OSError as exc:
            logger.warning("Could not prune automatic backup %s: %s", old_path, exc)
    return True, result


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
        logger.warning("Rejected invalid backup '%s': %s", backup_filepath, reason)
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
            logger.error("Restored DB failed integrity check: %s", restored_reason)
            return False, f"Restore failed its integrity check. Safety backup: {safety_path}"

        reset_thread_connections()
        logger.info("Database successfully restored from: %s", backup_filepath)
        return True, "Backup restored successfully."
    except Exception as exc:
        logger.error("Database restore failed: %s", exc)
        return False, "Restore could not be completed. Your safety backup was kept."
