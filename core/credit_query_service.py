"""Fast read models for open customer-credit balances."""

from core.customer_service import escape_sql_like
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoCreditQuery")


def load_open_credit(text="", limit=200):
    raw = str(text or "").strip()
    safe_limit = max(1, min(int(limit), 500))
    escaped = escape_sql_like(raw)
    like = f"%{escaped}%"
    try:
        with get_db() as (_conn, cur):
            if raw:
                cur.execute(
                    "SELECT k.id, c.first_name || ' ' || c.last_name, k.purchase_id, "
                    "       k.amount_due, k.amount_paid, k.customer_id "
                    "FROM Customer_Khatoo k "
                    "JOIN Customers c ON c.id_card_number = k.customer_id "
                    "WHERE k.amount_due > 0 "
                    "  AND (c.id_card_number = %s OR c.first_name LIKE %s OR c.last_name LIKE %s) "
                    "ORDER BY k.id DESC " + f"LIMIT {safe_limit}",
                    (raw, like, like),
                )
            else:
                cur.execute(
                    "SELECT k.id, c.first_name || ' ' || c.last_name, k.purchase_id, "
                    "       k.amount_due, k.amount_paid, k.customer_id "
                    "FROM Customer_Khatoo k "
                    "JOIN Customers c ON c.id_card_number = k.customer_id "
                    "WHERE k.amount_due > 0 ORDER BY k.id DESC " + f"LIMIT {safe_limit}"
                )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Open credit lookup failed: %s", exc)
        return []


def total_open_credit():
    try:
        with get_db() as (_conn, cur):
            cur.execute("SELECT COALESCE(SUM(amount_due), 0) FROM Customer_Khatoo WHERE amount_due > 0")
            row = cur.fetchone()
            return float(row[0]) if row else 0.0
    except Exception as exc:
        logger.error("Credit summary failed: %s", exc)
        return 0.0
