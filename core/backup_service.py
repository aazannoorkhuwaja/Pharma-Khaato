import os
import sqlite3
from contextlib import closing
from datetime import datetime, date
from pathlib import Path

from core.path_manager import PathManager
from core.logger import get_logger

logger = get_logger("PharmaKhaatoBackup")
AUTO_BACKUP_PREFIX = "auto_pharmacy_db_backup"
DEFAULT_AUTO_BACKUP_RETENTION = 14
MIN_AUTO_BACKUP_RETENTION = 3
MAX_AUTO_BACKUP_RETENTION = 90


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


def _normalize_retention(retention) -> int:
    try:
        value = int(retention)
    except (TypeError, ValueError):
        value = DEFAULT_AUTO_BACKUP_RETENTION
    return max(MIN_AUTO_BACKUP_RETENTION, min(value, MAX_AUTO_BACKUP_RETENTION))


def _automatic_backups(backup_dir: str) -> list[tuple[float, str]]:
    autos: list[tuple[float, str]] = []
    for name in os.listdir(backup_dir):
        if not (name.startswith(AUTO_BACKUP_PREFIX + "_") and name.endswith(".sqlite")):
            continue
        path = os.path.join(backup_dir, name)
        try:
            stat = os.stat(path)
        except OSError:
            continue
        autos.append((stat.st_mtime, path))
    autos.sort(reverse=True)
    return autos


def _prune_automatic_backups(autos: list[tuple[float, str]], retention: int) -> None:
    """Prune only automatic snapshots; manual and migration backups are never touched."""
    for _mtime, old_path in autos[retention:]:
        try:
            os.remove(old_path)
            logger.info("Pruned expired automatic backup: %s", old_path)
        except OSError as exc:
            logger.warning("Could not prune automatic backup %s: %s", old_path, exc)


def ensure_daily_backup(retention=DEFAULT_AUTO_BACKUP_RETENTION):
    """Create at most one valid automatic backup per local day and enforce retention.

    The newest ``retention`` automatic snapshots are kept (default 14, clamped to
    3..90). Cleanup runs even when today's backup already exists. Manual backups
    and pre-migration safety backups are never removed by this policy.
    """
    retention = _normalize_retention(retention)
    backup_dir = PathManager.get_backups_dir()
    os.makedirs(backup_dir, exist_ok=True)
    today = date.today()

    autos = _automatic_backups(backup_dir)
    for mtime, path in autos:
        if datetime.fromtimestamp(mtime).date() != today:
            continue
        valid, _reason = _validate_sqlite_database(path)
        if valid:
            _prune_automatic_backups(autos, retention)
            return True, path

    ok, result = backup_database(AUTO_BACKUP_PREFIX)
    if not ok:
        return False, result

    autos.append((os.path.getmtime(result), result))
    autos.sort(reverse=True)
    _prune_automatic_backups(autos, retention)
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

    safety_path = None
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
            return False, (
                "Restore failed its integrity check. No further restore attempts were made. "
                f"Your pre-restore safety backup is: {safety_path}. See docs/RECOVERY.md."
            )

        reset_thread_connections()
        logger.info("Database successfully restored from: %s", backup_filepath)
        return True, "Backup restored successfully."
    except Exception as exc:
        logger.error("Database restore failed: %s", exc)
        if safety_path:
            return False, (
                "Restore could not be completed. Keep the application closed until the database "
                f"is checked. Your pre-restore safety backup is: {safety_path}. See docs/RECOVERY.md."
            )
        return False, "Restore could not be completed. See docs/RECOVERY.md before retrying."
