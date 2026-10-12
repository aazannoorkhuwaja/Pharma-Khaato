import os
import shutil
import sqlite3
from datetime import datetime
from core.path_manager import PathManager
from core.logger import get_logger

logger = get_logger("PharmaKhaatoBackup")

def backup_database():
    """
    Creates a timestamped snapshot of the live SQLite database file.
    Returns (success: bool, filepath_or_msg: str).
    """
    db_path = PathManager.get_db_path()
    if not os.path.exists(db_path):
        return False, "Database file does not exist."

    try:
        backup_dir = PathManager.get_backups_dir()
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dest_filename = f"pharmacy_db_backup_{ts}.sqlite"
        dest_path = os.path.join(backup_dir, dest_filename)

        # Use SQLite backup API for online atomic snapshot
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(dest_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        logger.info(f"Database snapshot successfully created: {dest_path}")
        return True, dest_path
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return False, f"Backup failed: {e}"

def create_db_backup():
    """Alias for backup_database."""
    return backup_database()

def list_backups():
    """Returns list of dictionary metadata for existing database backup files."""
    backup_dir = PathManager.get_backups_dir()
    if not os.path.exists(backup_dir):
        return []
    files = []
    for fname in os.listdir(backup_dir):
        if fname.endswith(".sqlite"):
            fpath = os.path.join(backup_dir, fname)
            st = os.stat(fpath)
            ctime_str = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            files.append({
                "filename": fname,
                "filepath": fpath,
                "size_bytes": st.st_size,
                "created_at": ctime_str
            })
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return files

def restore_database(backup_filepath):
    """
    Restores the database from a specified backup file after creating a safety backup
    and safely resetting thread-local connections.
    Returns (success: bool, msg: str).
    """
    db_path = PathManager.get_db_path()
    if not os.path.exists(backup_filepath):
        return False, f"Backup file not found at: {backup_filepath}"

    try:
        from core.db_engine import reset_thread_connections
        reset_thread_connections()

        # Create automatic safety backup before restoring
        ok, safety_path = backup_database()
        if not ok:
            logger.warning(f"Could not create safety backup before restore: {safety_path}")

        # Perform atomic restore
        dst_conn = sqlite3.connect(db_path)
        src_conn = sqlite3.connect(backup_filepath)
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()

        reset_thread_connections()
        logger.info(f"Database successfully restored from: {backup_filepath}")
        return True, "Database successfully restored from backup snapshot."
    except Exception as e:
        logger.error(f"Database restore failed: {e}")
        return False, f"Restore failed: {e}"
