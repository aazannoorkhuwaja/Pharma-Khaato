"""Low-latency sellable product lookup for the POS counter."""

import re

from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoProductSearch")
_MAX_RESULTS = 40


def _row_for_exact_code(code: str):
    with get_db() as (_conn, cur):
        cur.execute(
            "SELECT p.id, p.product_name, p.price, "
            "       (SELECT b.id FROM Batch b WHERE b.product_id = p.id "
            "        AND b.quantity > 0 AND b.expiry_date > DATE('now') "
            "        ORDER BY b.expiry_date ASC, b.id ASC LIMIT 1), "
            "       (SELECT COALESCE(SUM(b.quantity), 0) FROM Batch b "
            "        WHERE b.product_id = p.id AND b.quantity > 0 AND b.expiry_date > DATE('now')), "
            "       (SELECT b.expiry_date FROM Batch b WHERE b.product_id = p.id "
            "        AND b.quantity > 0 AND b.expiry_date > DATE('now') "
            "        ORDER BY b.expiry_date ASC, b.id ASC LIMIT 1) "
            "FROM Products p "
            "WHERE p.is_active = 1 AND (p.barcode = %s OR p.sku = %s OR p.alternate_barcode = %s) "
            "LIMIT 1",
            (code, code, code),
        )
        row = cur.fetchone()
    if row and row[3] is not None:
        return row
    return None


def get_product_by_barcode(code: str):
    code = str(code or "").strip()
    if not code:
        return None
    try:
        return _row_for_exact_code(code)
    except Exception as exc:
        logger.error("Exact product lookup failed: %s", exc)
        return None


def _fts_query(term: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", term)
    return " ".join(f"{token}*" for token in tokens[:8])


def search_sellable_products(term: str):
    """Search product master once per product and return total sellable stock.

    FTS5 handles names/formulas/generics quickly. Exact barcode/SKU lookup takes
    a direct indexed path. Results are bounded so typing stays responsive even
    with a large catalog.
    """
    raw = str(term or "").strip()
    if not raw:
        return []

    exact = get_product_by_barcode(raw)
    if exact:
        return [exact]

    query = _fts_query(raw)
    try:
        with get_db() as (_conn, cur):
            if query:
                cur.execute(
                    "SELECT p.id, p.product_name, p.price, "
                    "       (SELECT b.id FROM Batch b WHERE b.product_id = p.id "
                    "        AND b.quantity > 0 AND b.expiry_date > DATE('now') "
                    "        ORDER BY b.expiry_date ASC, b.id ASC LIMIT 1), "
                    "       (SELECT COALESCE(SUM(b.quantity), 0) FROM Batch b "
                    "        WHERE b.product_id = p.id AND b.quantity > 0 AND b.expiry_date > DATE('now')), "
                    "       (SELECT b.expiry_date FROM Batch b WHERE b.product_id = p.id "
                    "        AND b.quantity > 0 AND b.expiry_date > DATE('now') "
                    "        ORDER BY b.expiry_date ASC, b.id ASC LIMIT 1) "
                    "FROM product_fts f JOIN Products p ON p.id = CAST(f.product_id AS INTEGER) "
                    "WHERE product_fts MATCH %s AND p.is_active = 1 "
                    "AND EXISTS (SELECT 1 FROM Batch bx WHERE bx.product_id = p.id "
                    "            AND bx.quantity > 0 AND bx.expiry_date > DATE('now')) "
                    "ORDER BY bm25(product_fts), p.product_name ASC "
                    f"LIMIT {_MAX_RESULTS}",
                    (query,),
                )
                rows = cur.fetchall()
                if rows:
                    return rows

            like = f"%{raw.replace('%', '').replace('_', '')}%"
            cur.execute(
                "SELECT p.id, p.product_name, p.price, "
                "       (SELECT b.id FROM Batch b WHERE b.product_id = p.id "
                "        AND b.quantity > 0 AND b.expiry_date > DATE('now') "
                "        ORDER BY b.expiry_date ASC, b.id ASC LIMIT 1), "
                "       (SELECT COALESCE(SUM(b.quantity), 0) FROM Batch b "
                "        WHERE b.product_id = p.id AND b.quantity > 0 AND b.expiry_date > DATE('now')), "
                "       (SELECT b.expiry_date FROM Batch b WHERE b.product_id = p.id "
                "        AND b.quantity > 0 AND b.expiry_date > DATE('now') "
                "        ORDER BY b.expiry_date ASC, b.id ASC LIMIT 1) "
                "FROM Products p WHERE p.is_active = 1 "
                "AND (p.product_name LIKE %s OR p.formula LIKE %s OR p.generic_name LIKE %s) "
                "AND EXISTS (SELECT 1 FROM Batch bx WHERE bx.product_id = p.id "
                "            AND bx.quantity > 0 AND bx.expiry_date > DATE('now')) "
                "ORDER BY p.product_name ASC "
                f"LIMIT {_MAX_RESULTS}",
                (like, like, like),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Product search failed: %s", exc)
        return []
