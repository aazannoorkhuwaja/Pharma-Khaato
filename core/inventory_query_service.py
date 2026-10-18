"""Read-optimized inventory queries for responsive desktop screens.

Routine views deliberately materialize bounded working sets. Counts are queried
separately so the UI can still tell the truth about the full database while a
large catalog is searched on demand.
"""

from datetime import date, timedelta

from core.business_time import business_date
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoInventoryQuery")

_STOCK_CTE = (
    "WITH catalog AS (SELECT p.*,COALESCE(s.sellable_stock,0) AS sellable_stock "
    "FROM Products p LEFT JOIN (SELECT product_id,SUM(quantity) AS sellable_stock FROM Batch "
    "WHERE quantity>0 AND expiry_date>=%s AND stock_status='SELLABLE' GROUP BY product_id) s "
    "ON s.product_id=p.id) "
)



def _safe_limit(value, default: int, minimum: int = 10, maximum: int = 1000) -> int:
    try:
        return max(minimum, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def catalog_snapshot(product_limit: int = 400, alert_limit: int = 100) -> dict:
    """Return the default Stock & Products working set in one DB session.

    Product rows include each product's reorder level so the catalog can derive
    status correctly even when the separate alert table itself is bounded.
    """
    product_limit = _safe_limit(product_limit, 400, 50, 1000)
    alert_limit = _safe_limit(alert_limit, 100, 25, 300)
    today = business_date().isoformat()
    cutoff = (business_date() + timedelta(days=30)).isoformat()

    empty = {
        "products": [],
        "total_products": 0,
        "low_stock": [],
        "low_stock_count": 0,
        "near_expiry": [],
        "near_expiry_count": 0,
        "product_limit": product_limit,
    }
    try:
        with get_db() as (_conn, cur):
            cur.execute("SELECT COUNT(*) FROM Products")
            row = cur.fetchone()
            total_products = int(row[0] or 0) if row else 0

            cur.execute(
                _STOCK_CTE + "SELECT id,product_name,price,sellable_stock,min_stock,base_unit,is_active "
                "FROM catalog ORDER BY product_name ASC " + f"LIMIT {product_limit}", (today,)
            )
            products = cur.fetchall()

            cur.execute(
                _STOCK_CTE + "SELECT COUNT(*) FROM catalog "
                "WHERE is_active=1 AND sellable_stock <= min_stock", (today,)
            )
            row = cur.fetchone()
            low_count = int(row[0] or 0) if row else 0

            cur.execute(
                _STOCK_CTE + "SELECT product_name,sellable_stock,min_stock FROM catalog "
                "WHERE is_active=1 AND sellable_stock<=min_stock "
                "ORDER BY sellable_stock ASC,product_name ASC " + f"LIMIT {alert_limit}", (today,)
            )
            low_stock = cur.fetchall()

            cur.execute(
                "SELECT COUNT(*) "
                "FROM Batch b "
                "WHERE b.expiry_date >= %s AND b.expiry_date <= %s AND b.quantity > 0 AND b.stock_status='SELLABLE'",
                (today, cutoff),
            )
            row = cur.fetchone()
            near_count = int(row[0] or 0) if row else 0

            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date >= %s AND b.expiry_date <= %s AND b.quantity > 0 AND b.stock_status='SELLABLE' "
                "ORDER BY b.expiry_date ASC, b.id ASC " + f"LIMIT {alert_limit}",
                (today, cutoff),
            )
            near_expiry = cur.fetchall()

        return {
            "products": products,
            "total_products": total_products,
            "low_stock": low_stock,
            "low_stock_count": low_count,
            "near_expiry": near_expiry,
            "near_expiry_count": near_count,
            "product_limit": product_limit,
        }
    except Exception as exc:
        logger.error("Inventory catalog snapshot failed: %s", exc)
        raise RuntimeError("Could not load stock. Try again.") from exc


def search_catalog_products(term: str, limit: int = 150):
    """Search the product master, including zero-stock products.

    Exact barcode/SKU matches are placed first. This differs from POS search,
    which intentionally returns only sellable batches. Reorder level travels
    with every result so status remains authoritative outside the first page.
    """
    value = str(term or "").strip()
    if not value:
        return []
    limit = _safe_limit(limit, 150, 10, 300)
    safe = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{safe}%"
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                _STOCK_CTE + "SELECT id,product_name,price,sellable_stock,min_stock,base_unit,is_active "
                "FROM catalog "
                "WHERE barcode = %s OR sku = %s OR alternate_barcode = %s "
                "   OR product_name LIKE %s OR formula LIKE %s OR generic_name LIKE %s "
                "   OR id IN (SELECT product_id FROM Product_Code WHERE code=%s) "
                "ORDER BY CASE WHEN barcode = %s OR sku = %s OR alternate_barcode = %s "
                "              THEN 0 ELSE 1 END, product_name ASC "
                + f"LIMIT {limit}",
                (business_date().isoformat(),value, value, value, like, like, like,value, value, value, value),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Inventory catalog search failed: %s", exc)
        raise RuntimeError("Could not load stock. Try again.") from exc


def active_batches(limit: int = 300):
    """Return the nearest-expiry sellable batches, bounded for responsive UI."""
    safe_limit = _safe_limit(limit, 300, 25, 1000)

    try:
        today = business_date().isoformat()
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date >= %s AND b.quantity > 0 AND b.stock_status='SELLABLE' "
                "ORDER BY b.expiry_date ASC, b.id ASC " + f"LIMIT {safe_limit}",
                (today,),
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Bounded active batch query failed: %s", exc)
        raise RuntimeError("Could not load stock. Try again.") from exc
