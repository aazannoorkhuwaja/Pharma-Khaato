import json
from datetime import datetime
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoAudit")


def log_audit_event(user_id, action, details=""):
    """
    Logs an enterprise audit event to the Audit_Log database table.
    """
    try:
        with get_db() as (conn, cur):
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
            cur.execute(
                "INSERT INTO Audit_Log (timestamp, user_id, action, details) VALUES (%s, %s, %s, %s)",
                (now_str, str(user_id), str(action), details_str),
            )
        return True
    except Exception as e:
        logger.error(f"Audit log insertion error: {e}")
        return False


def get_audit_logs(limit=100):
    """
    Fetches recent audit log entries.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, timestamp, user_id, action, details "
                "FROM Audit_Log ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Fetch audit log error: {e}")
        return []
