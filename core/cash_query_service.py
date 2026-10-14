"""Read-optimized cash-shift queries used by the desktop UI."""

from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoCashQuery")


def get_session_movements(session_id: int, limit: int = 50):
    """Return recent manual cash entries for one shift using the session index."""
    try:
        session_id = int(session_id)
        safe_limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        return []

    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT id, session_id, movement_type, amount, reason, created_at "
                "FROM Cash_Movement WHERE session_id = %s "
                "ORDER BY id DESC " + f"LIMIT {safe_limit}",
                (session_id,),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Session cash movement query failed: %s", exc)
        return []
