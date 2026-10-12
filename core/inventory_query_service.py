"""Read-optimized inventory queries for UI screens.

These queries are intentionally bounded. A desktop table should never try to
materialize an unlimited multi-year batch ledger just because a tab was opened.
"""

from datetime import date

from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoInventoryQuery")


def active_batches(limit: int = 300):
    """Return the nearest-expiry sellable batches, bounded for responsive UI."""
    try:
        safe_limit = max(25, min(int(limit), 1000))
    except (TypeError, ValueError):
        safe_limit = 300

    try:
        today = date.today().isoformat()
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date > %s AND b.quantity > 0 "
                "ORDER BY b.expiry_date ASC, b.id ASC " + f"LIMIT {safe_limit}",
                (today,),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Bounded active batch query failed: %s", exc)
        return []
