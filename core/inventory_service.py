import time
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoInventory")

# In-memory TTL Cache (5 sec TTL for high concurrency UI responsiveness)
_CACHE: dict = {}
_CACHE_TTL = 5.0  # seconds


def _get_cached(key):
    if key in _CACHE:
        val, timestamp = _CACHE[key]
        if time.time() - timestamp < _CACHE_TTL:
            return val
    return None


def _set_cache(key, val):
    _CACHE[key] = (val, time.time())


def clear_inventory_cache():
    """Invalidates inventory cache upon stock/product mutations."""
    global _CACHE
    _CACHE.clear()


def search_products(keyword=""):
    """
    Search available non-expired products in stock with 5s TTL caching.
    Matches product_name, barcode, SKU, generic_name, or formula.
    Returns list of tuples: (product_id, product_name, price, batch_id, batch_quantity, expiry_date)
    """
    kw = keyword.strip()
    safe_kw = kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    cache_key = f"search_{safe_kw}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT p.id, p.product_name, p.price, b.id, b.quantity, b.expiry_date "
                "FROM Products p "
                "JOIN Batch b ON b.product_id = p.id "
                "WHERE (p.product_name LIKE %s OR p.formula LIKE %s OR p.barcode = %s "
                "       OR p.sku = %s OR p.generic_name LIKE %s) "
                "  AND b.quantity > 0 "
                "  AND b.expiry_date > CURDATE() "
                "ORDER BY b.expiry_date ASC",
                (f"%{safe_kw}%", f"%{safe_kw}%", kw, kw, f"%{safe_kw}%"),
            )
            res = cur.fetchall()
        _set_cache(cache_key, res)
        return res
    except Exception as e:
        logger.error(f"Product search error: {e}")
        return []


def get_product_by_barcode(barcode):
    """Fetches exact product record by barcode or SKU."""
    if not barcode:
        return None
    code = barcode.strip()
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT p.id, p.product_name, p.price, b.id, b.quantity, b.expiry_date "
                "FROM Products p "
                "JOIN Batch b ON b.product_id = p.id "
                "WHERE (p.barcode = %s OR p.sku = %s OR p.alternate_barcode = %s) "
                "  AND b.quantity > 0 AND b.expiry_date > CURDATE() "
                "ORDER BY b.expiry_date ASC LIMIT 1",
                (code, code, code),
            )
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Barcode lookup error: {e}")
        return None


def get_all_products():
    """Returns list of tuples: (id, product_name, price, stock_quantity) with TTL cache."""
    cache_key = "all_products"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, product_name, price, stock_quantity FROM Products ORDER BY product_name ASC"
            )
            res = cur.fetchall()
        _set_cache(cache_key, res)
        return res
    except Exception as e:
        logger.error(f"Get all products error: {e}")
        return []


def get_all_suppliers():
    """Returns list of tuples: (id, supplier_name, supplier_company_name) with TTL cache."""
    cache_key = "all_suppliers"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, supplier_name, supplier_company_name FROM Supplier ORDER BY supplier_name ASC"
            )
            res = cur.fetchall()
        _set_cache(cache_key, res)
        return res
    except Exception as e:
        logger.error(f"Get all suppliers error: {e}")
        return []


def register_product(
    name, price, min_stock=10, company="General", category="Surgical", formula="N/A",
    barcode=None, sku=None, generic_name=None, dosage_form="Tablet", strength="N/A",
    pack_size=1, rack_location="Unassigned", requires_prescription=0, tax_rate=0.0
):
    """Adds a new master product entry with complete metadata & bounds validation."""
    try:
        dec_price = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        min_stock = int(min_stock)
        pack_size = int(pack_size)
        tax_rate = float(tax_rate)
        if dec_price <= Decimal("0.00"):
            return False, "Price must be greater than zero."
        if min_stock < 0:
            return False, "Minimum stock threshold cannot be negative."
        if pack_size < 1:
            return False, "Pack size must be at least 1."
    except (ValueError, TypeError):
        return False, "Invalid price or numerical attribute specified."

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT id FROM Products WHERE product_name = %s", (name,))
            if cur.fetchone():
                raise ValueError(f"Product '{name}' already exists in inventory master list.")
            if barcode:
                cur.execute("SELECT id FROM Products WHERE barcode = %s", (barcode,))
                if cur.fetchone():
                    raise ValueError(f"Barcode '{barcode}' is already assigned to another product.")
            cur.execute(
                "INSERT INTO Products "
                "(product_name, company_name, category, price, stock_quantity, min_stock, formula, "
                "barcode, sku, generic_name, dosage_form, strength, pack_size, rack_location, "
                "requires_prescription, tax_rate) "
                "VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    name, company, category, float(dec_price), min_stock, formula,
                    barcode, sku, generic_name, dosage_form, strength, pack_size,
                    rack_location, requires_prescription, tax_rate,
                ),
            )
        clear_inventory_cache()
        return True, f"Product '{name}' registered successfully."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Product registration failed: {e}"


def register_supplier(name, contact_phone, company_name=None, email="info@supplier.com"):
    """Adds a new supplier entry."""
    if not company_name:
        company_name = name
    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT id FROM Supplier WHERE supplier_name = %s", (name,))
            if cur.fetchone():
                raise ValueError(f"Supplier '{name}' already exists.")
            cur.execute(
                "INSERT INTO Supplier (supplier_name, supplier_company_name, Email_address, phone_number) "
                "VALUES (%s, %s, %s, %s)",
                (name, company_name, email, contact_phone),
            )
        clear_inventory_cache()
        return True, f"Supplier '{name}' registered successfully."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Supplier registration failed: {e}"


def add_batch(prod_id, supp_id, qty, expiry_date, manufacture_date=None):
    """Adds a new stock shipment batch and updates total product stock."""
    try:
        qty = int(qty)
        if qty <= 0:
            return False, "Batch quantity must be greater than zero."
    except (ValueError, TypeError):
        return False, "Invalid batch quantity specified."

    if not manufacture_date:
        manufacture_date = date.today().strftime("%Y-%m-%d")

    # Accept common loose formats ('2027-1-5', '2027/01/05') and store strict
    # ISO — FEFO ordering and the expiry guard rely on padded text comparison.
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            exp_dt = datetime.strptime(str(expiry_date).strip(), fmt).date()
            break
        except ValueError:
            continue
    else:
        return False, f"Invalid expiry date format: '{expiry_date}'. Expected YYYY-MM-DD."
    expiry_date = exp_dt.isoformat()

    try:
        if exp_dt <= date.today():
            return False, f"Expiry date ({expiry_date}) has already passed! Expired stock cannot be added."
    except NameError:
        return False, f"Invalid expiry date format: '{expiry_date}'."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "INSERT INTO Batch "
                "(number_of_product, expiry_date, product_id, supplier_id, quantity, manufacture_Date) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (qty, expiry_date, prod_id, supp_id, qty, manufacture_date),
            )
            cur.execute(
                "UPDATE Products SET stock_quantity = stock_quantity + %s WHERE id = %s",
                (qty, prod_id),
            )
        clear_inventory_cache()
        return True, "Stock shipment batch recorded successfully."
    except Exception as e:
        return False, f"Batch creation failed: {e}"


def get_stocks_by_supplier(supplier_id):
    """Returns all batch stocks for a given supplier."""
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT p.product_name, b.id, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "WHERE b.supplier_id = %s AND b.quantity > 0 "
                "ORDER BY b.expiry_date ASC",
                (supplier_id,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Supplier stock report error: {e}")
        return []


def get_all_active_batches():
    """Returns all non-expired, sellable batches ordered by FEFO (expiry_date ASC)."""
    try:
        with get_db() as (conn, cur):
            today = date.today().strftime("%Y-%m-%d")
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date > %s AND b.quantity > 0 "
                "ORDER BY b.expiry_date ASC, b.id ASC",
                (today,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Get all active batches error: {e}")
        return []


def get_near_expiry(days=30):
    """Returns batches expiring within specified days."""
    try:
        with get_db() as (conn, cur):
            today = date.today().strftime("%Y-%m-%d")
            cutoff = (date.today() + timedelta(days=int(days))).strftime("%Y-%m-%d")
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date >= %s AND b.expiry_date <= %s AND b.quantity > 0 "
                "ORDER BY b.expiry_date ASC",
                (today, cutoff),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Near expiry fetch error: {e}")
        return []


def get_expired_stock():
    """Returns expired stock batches."""
    try:
        with get_db() as (conn, cur):
            today = date.today().strftime("%Y-%m-%d")
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date < %s AND b.quantity > 0 "
                "ORDER BY b.expiry_date ASC",
                (today,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Expired stock fetch error: {e}")
        return []


def get_low_stock_products(threshold=None):
    """Returns list of products whose stock_quantity <= min_stock or specified threshold."""
    try:
        with get_db() as (conn, cur):
            if threshold is not None:
                cur.execute(
                    "SELECT product_name, stock_quantity, min_stock "
                    "FROM Products WHERE CAST(stock_quantity AS NUMERIC) <= %s "
                    "ORDER BY CAST(stock_quantity AS NUMERIC) ASC",
                    (threshold,),
                )
            else:
                cur.execute(
                    "SELECT product_name, stock_quantity, min_stock "
                    "FROM Products WHERE CAST(stock_quantity AS NUMERIC) <= CAST(min_stock AS NUMERIC) "
                    "ORDER BY CAST(stock_quantity AS NUMERIC) ASC"
                )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Low stock fetch error: {e}")
        return []
