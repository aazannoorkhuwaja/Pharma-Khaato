"""Bounded customer lookups for responsive counter and directory screens."""

from core.customer_service import escape_sql_like, validate_cnic
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoCustomerDirectory")


def search_customers(text="", limit=80):
    raw = str(text or "").strip()
    if not raw:
        return []
    safe_limit = max(1, min(int(limit), 250))
    try:
        with get_db() as (_conn, cur):
            exact_id = validate_cnic(raw)
            if exact_id:
                cur.execute(
                    "SELECT id_card_number, first_name, last_name, Email_Address, city "
                    "FROM Customers WHERE id_card_number = %s LIMIT 1",
                    (exact_id,),
                )
                exact = cur.fetchall()
                if exact:
                    return exact

            escaped = escape_sql_like(raw)
            like = f"%{escaped}%"
            cur.execute(
                "SELECT id_card_number, first_name, last_name, Email_Address, city "
                "FROM Customers "
                "WHERE id_card_number LIKE %s OR first_name LIKE %s OR last_name LIKE %s "
                "ORDER BY first_name ASC, last_name ASC " + f"LIMIT {safe_limit}",
                (like, like, like),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Customer lookup failed: %s", exc)
        return []


def search_customers_with_debt(text="", limit=240):
    raw = str(text or "").strip()
    safe_limit = max(1, min(int(limit), 500))
    escaped = escape_sql_like(raw)
    like = f"%{escaped}%"
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT c.id_card_number, c.first_name, c.last_name, c.Email_Address, c.city, "
                "       COALESCE(SUM(k.amount_due), 0.0) AS total_debt "
                "FROM Customers c "
                "LEFT JOIN Customer_Khatoo k ON k.customer_id = c.id_card_number "
                "WHERE c.id_card_number LIKE %s OR c.first_name LIKE %s OR c.last_name LIKE %s "
                "GROUP BY c.id_card_number, c.first_name, c.last_name, c.Email_Address, c.city "
                "ORDER BY c.first_name ASC, c.last_name ASC " + f"LIMIT {safe_limit}",
                (like, like, like),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Customer directory lookup failed: %s", exc)
        return []
