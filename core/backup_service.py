import os
import sqlite3
import json
import shutil
import time
import uuid
from contextlib import closing
from datetime import datetime, date
from pathlib import Path

from core.path_manager import PathManager
from core.logger import get_logger

logger = get_logger("PharmaKhaatoBackup")
AUTO_BACKUP_PREFIX = "auto_pharmacy_db_backup"
_BACKUP_TABLES = {"Employee", "Customers", "Supplier", "Products", "Batch", "Purchase", "Sales_details", "Receipt"}
_COPIED_SNAPSHOTS = {}


def backup_destination():
    configured = os.getenv("PHARMA_KHAATO_BACKUP_DIR", "").strip()
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    try:
        with open(os.path.join(PathManager.get_config_dir(), "backup.json"), encoding="utf-8") as handle:
            return str(json.load(handle).get("destination", ""))
    except (OSError, ValueError, TypeError):
        return ""


def configure_backup_destination(destination):
    """Persist a local operator-selected backup directory without storing secrets."""
    path = os.path.abspath(os.path.expanduser(str(destination))) if destination else ""
    if path:
        os.makedirs(path, exist_ok=True)
        if os.path.samefile(path, PathManager.get_backups_dir()):
            return False, "Choose another device or folder for the second backup copy."
    target = os.path.join(PathManager.get_config_dir(), "backup.json")
    temporary = target + ".partial"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump({"destination": path, "device": os.stat(path).st_dev if path else None}, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
    return True, "Backup destination saved."


def _snapshot(source, target):
    deadline = time.monotonic() + 15
    def progress(_status, _remaining, _total):
        if time.monotonic() > deadline:
            raise TimeoutError("The database is busy. Try the backup again after current work finishes.")
    source.backup(target, pages=128, progress=progress, sleep=0.05)


def _sync_directory(directory):
    if os.name != "nt":
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def recover_interrupted_restore():
    """Resolve a persisted swap journal before SQLite can create a fresh store."""
    journal = os.path.join(PathManager.get_config_dir(), "restore-pending.json")
    if not os.path.exists(journal):
        return
    with open(journal, encoding="utf-8") as handle:
        state = json.load(handle)
    live = PathManager.get_db_path()
    quarantine = os.path.abspath(state["quarantine"])
    if os.path.commonpath((quarantine, os.path.abspath(PathManager.get_backups_dir()))) != os.path.abspath(PathManager.get_backups_dir()):
        raise RuntimeError("The recovery journal needs support review.")
    valid = os.path.exists(live) and _validate_sqlite_database(live)[0]
    if not valid:
        for suffix in ("", "-wal", "-shm"):
            previous = os.path.join(quarantine, os.path.basename(live + suffix))
            if os.path.exists(previous):
                os.replace(previous, live + suffix)
    stage = state.get("stage", "")
    if stage.startswith(live + ".restore-"):
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(stage + suffix):
                os.remove(stage + suffix)
    os.remove(journal)
    _sync_directory(os.path.dirname(live))


def _copy_external(snapshot):
    destination = backup_destination()
    if not destination:
        return
    if not os.path.isdir(destination):
        raise OSError("The second backup device is disconnected.")
    if not os.getenv("PHARMA_KHAATO_BACKUP_DIR", "").strip():
        with open(os.path.join(PathManager.get_config_dir(), "backup.json"), encoding="utf-8") as handle:
            saved_device = json.load(handle).get("device")
        if saved_device is not None and os.stat(destination).st_dev != saved_device:
            raise OSError("The configured backup device is not mounted.")
    target = os.path.join(destination, os.path.basename(snapshot))
    if os.path.exists(target):
        current = (os.stat(snapshot).st_mtime_ns, os.stat(snapshot).st_size,
                   os.stat(target).st_mtime_ns, os.stat(target).st_size)
        if _COPIED_SNAPSHOTS.get(target) == current:
            return
    temporary = target + ".partial"
    try:
        with open(snapshot, "rb") as source, open(temporary, "wb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        valid, reason = _validate_sqlite_database(temporary)
        if not valid:
            raise ValueError(reason)
        os.replace(temporary, target)
        _COPIED_SNAPSHOTS[target] = (os.stat(snapshot).st_mtime_ns, os.stat(snapshot).st_size,
                                    os.stat(target).st_mtime_ns, os.stat(target).st_size)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _validate_sqlite_database(path: str) -> tuple[bool, str]:
    """Validate that a file is an intact SQLite database before trusting it."""
    try:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            row = conn.execute("PRAGMA quick_check;").fetchone()
            if not row or str(row[0]).lower() != "ok":
                return False, "Database integrity check failed."
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not _BACKUP_TABLES.issubset(tables):
                return False, "Required Pharma Khaato tables are missing."
            columns = {row[1] for row in conn.execute("PRAGMA table_info(Employee)")}
            if not {"Employee_id", "username", "password", "occupation"}.issubset(columns):
                return False, "Staff records are not a supported format."
            if conn.execute("PRAGMA foreign_key_check").fetchone():
                return False, "The backup contains inconsistent records."
            if "schema_migrations" in tables:
                from core.migration_manager import MigrationManager
                folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
                known = {os.path.basename(path) for path in MigrationManager._migration_catalog(folder)}
                applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
                if applied - known:
                    return False, "This backup requires a different application version."
        return True, "ok"
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
                _snapshot(src_conn, dst_conn)
                dst_conn.commit()

        valid, reason = _validate_sqlite_database(temp_path)
        if not valid:
            raise sqlite3.DatabaseError(f"Backup integrity check failed: {reason}")

        os.replace(temp_path, dest_path)
        try:
            _copy_external(dest_path)
        except (OSError, ValueError) as exc:
            logger.warning("Local backup saved but second backup copy failed: %s", exc)
            return False, "A local backup was saved, but the second backup location is unavailable. Reconnect it and try again."
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


def ensure_daily_backup(retention=14, max_age_seconds=3600):
    """Keep an hourly automatic snapshot, including across day boundaries.

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
        if datetime.fromtimestamp(stat.st_mtime).date() == today and time.time() - stat.st_mtime < max_age_seconds:
            valid, _reason = _validate_sqlite_database(path)
            if valid:
                try:
                    _copy_external(path)
                except (OSError, ValueError):
                    return False, "The second backup location is unavailable. Reconnect it and try again."
                return True, path

    ok, result = backup_database(AUTO_BACKUP_PREFIX)
    if not ok:
        return False, result

    autos.append((os.path.getmtime(result), result))
    autos.sort(reverse=True)
    cutoff = time.time() - retention * 86400
    for modified_at, old_path in autos[1:]:
        if modified_at >= cutoff:
            continue
        try:
            os.remove(old_path)
        except OSError as exc:
            logger.warning("Could not prune automatic backup %s: %s", old_path, exc)
    external = backup_destination()
    if external and os.path.isdir(external):
        for name in os.listdir(external):
            if name.startswith(AUTO_BACKUP_PREFIX + "_") and name.endswith(".sqlite"):
                old_path = os.path.join(external, name)
                try:
                    if os.path.getmtime(old_path) < cutoff:
                        os.remove(old_path)
                        _COPIED_SNAPSHOTS.pop(old_path, None)
                except OSError as exc:
                    logger.warning("Could not prune second automatic backup: %s", exc)
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


def restore_database(backup_filepath, require_restart=False):
    """Stage, migrate and validate before replacing live data under maintenance.

    Healthy originals receive a verified snapshot. Damaged originals and their
    journals are preserved as raw recovery evidence rather than blocking repair.
    """
    db_path = PathManager.get_db_path()
    if not os.path.exists(backup_filepath):
        return False, "The selected backup file no longer exists."

    valid, reason = _validate_sqlite_database(backup_filepath)
    if not valid:
        logger.warning("Rejected invalid backup '%s': %s", backup_filepath, reason)
        return False, "This backup file is damaged or is not a valid Pharma-Khaato database."

    stage = db_path + ".restore-" + uuid.uuid4().hex
    moved = []
    journal = os.path.join(PathManager.get_config_dir(), "restore-pending.json")
    try:
        from core.db_engine import database_maintenance
        from core.migration_manager import MigrationManager
        with database_maintenance():
            with closing(sqlite3.connect(stage)) as dst_conn:
                with closing(sqlite3.connect(Path(backup_filepath).resolve().as_uri() + "?mode=ro", uri=True)) as src_conn:
                    _snapshot(src_conn, dst_conn)
                dst_conn.execute("PRAGMA foreign_keys=ON")
                MigrationManager.apply_migrations(dst_conn)
                dst_conn.commit()
            restored_ok, restored_reason = _validate_sqlite_database(stage)
            if not restored_ok:
                raise ValueError(restored_reason)
            with open(stage, "rb") as durable_stage:
                os.fsync(durable_stage.fileno())
            quarantine = os.path.join(PathManager.get_backups_dir(), "before_restore_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
            os.makedirs(quarantine)
            with open(journal + ".partial", "w", encoding="utf-8") as handle:
                json.dump({"stage": stage, "quarantine": quarantine}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(journal + ".partial", journal)
            _sync_directory(os.path.dirname(journal))
            for suffix in ("", "-wal", "-shm"):
                source = db_path + suffix
                if os.path.exists(source):
                    target = os.path.join(quarantine, os.path.basename(source))
                    os.replace(source, target)
                    moved.append((source, target))
            try:
                os.replace(stage, db_path)
                good, reason = _validate_sqlite_database(db_path)
                if not good:
                    raise ValueError(reason)
                _sync_directory(os.path.dirname(db_path))
            except Exception:
                if os.path.exists(db_path):
                    os.remove(db_path)
                for source, target in reversed(moved):
                    os.replace(target, source)
                moved.clear()
                raise
            logger.info("Database restored; previous files preserved in %s", quarantine)
            os.remove(journal)
            if require_restart:
                from core.db_engine import _RESTART_PATHS
                _RESTART_PATHS.add(db_path)
            from core.permission_service import clear_permission_cache
            clear_permission_cache()
            return True, "Backup restored successfully. Previous data was preserved. Restart the application."
    except Exception as exc:
        logger.error("Database restore failed: %s", exc)
        for source, target in reversed(moved):
            try:
                if os.path.exists(target):
                    os.replace(target, source)
            except OSError:
                logger.exception("Could not roll back original database file: %s", source)
        if os.path.exists(journal) and not any(os.path.exists(target) for _source, target in moved):
            os.remove(journal)
        return False, "Restore could not be completed. Your safety backup was kept."
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(stage + suffix)
            except FileNotFoundError:
                pass
