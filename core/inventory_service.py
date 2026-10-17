import time
import calendar
import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from core.db_engine import get_db
from core.business_time import business_date, business_now
from core.logger import get_logger
from core.unit_service import whole_quantity, unit_options, require_available_code, convert_quantity

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
    from core.product_search_service import search_sellable_products
    return search_sellable_products(keyword)


def get_product_by_barcode(barcode):
    from core.product_search_service import get_product_by_barcode as lookup
    return lookup(barcode)


def get_all_products():
    """Returns list of tuples: (id, product_name, price, stock_quantity) with TTL cache."""
    cache_key = "all_products"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT p.id,p.product_name,p.price,COALESCE(s.quantity,0) FROM Products p "
                "LEFT JOIN (SELECT product_id,SUM(quantity) AS quantity FROM Batch WHERE quantity>0 "
                "AND expiry_date>=%s AND stock_status='SELLABLE' GROUP BY product_id) s ON s.product_id=p.id "
                "WHERE p.is_active=1 ORDER BY p.product_name", (business_date().isoformat(),)
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
    pack_size=1, rack_location="Unassigned", requires_prescription=0, tax_rate=0.0,
    base_unit="unit", units_per_strip=1, units_per_box=1, unit_barcodes=None, operation_key=None,
):
    """Adds a new master product entry with complete metadata & bounds validation."""
    try:
        dec_price = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        name = str(name or "").strip()
        if not name:
            return False, "Enter a product name including its strength."
        min_stock = whole_quantity(min_stock, allow_zero=True)
        pack_size = whole_quantity(pack_size)
        units_per_strip = whole_quantity(units_per_strip)
        units_per_box = whole_quantity(units_per_box)
        unit_options(base_unit, units_per_strip, units_per_box, dec_price)
        tax_rate = float(tax_rate)
        if dec_price <= Decimal("0.00"):
            return False, "Price must be greater than zero."
        if min_stock < 0:
            return False, "Minimum stock threshold cannot be negative."
        if pack_size < 1:
            return False, "Pack size must be at least 1."
        if not dec_price.is_finite() or not Decimal(str(tax_rate)).is_finite() or tax_rate < 0:
            return False, "Enter a valid selling price and tax rate."
    except (InvalidOperation, ValueError, TypeError) as exc:
        return False, str(exc) or "Invalid price or numerical attribute specified."

    try:
        with get_db(immediate=True) as (conn, cur):
            if _operation(cur,operation_key,{"kind":"product-create","name":name,"price":str(dec_price),
                          "minimum":min_stock,"company":company,"category":category,"formula":formula,
                          "barcode":barcode,"sku":sku,"generic":generic_name,"dosage":dosage_form,
                          "strength":strength,"pack":pack_size,"rack":rack_location,"rx":requires_prescription,
                          "tax":tax_rate,"base":base_unit,"strip":units_per_strip,"box":units_per_box,
                          "codes":unit_barcodes}):
                return True,"This product was already saved."
            cur.execute("SELECT id FROM Products WHERE product_name = %s", (name,))
            if cur.fetchone():
                raise ValueError(f"Product '{name}' already exists in inventory master list.")
            barcode = require_available_code(cur, barcode) or None
            sku = require_available_code(cur, sku) or None
            codes = dict(unit_barcodes or {})
            if barcode:
                codes.setdefault("base", barcode)
            normalized_codes = _validated_codes(cur, codes, base_unit, units_per_strip, units_per_box)
            cur.execute(
                "INSERT INTO Products "
                "(product_name, company_name, category, price, stock_quantity, min_stock, formula, "
                "barcode, sku, generic_name, dosage_form, strength, pack_size, rack_location, "
                "requires_prescription, tax_rate, base_unit,units_per_strip,units_per_box) "
                "VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s)",
                (
                    name, company, category, float(dec_price), min_stock, formula,
                    barcode, sku, generic_name, dosage_form, strength, pack_size,
                    rack_location, requires_prescription, tax_rate,
                    str(base_unit or "unit").strip(), units_per_strip, units_per_box,
                ),
            )
            product_id = cur.lastrowid
            if sku and sku not in normalized_codes.values():
                normalized_codes["sku"] = sku
            for code_unit, code in normalized_codes.items():
                cur.execute("INSERT INTO Product_Code(code,product_id,unit_code) VALUES (%s,%s,%s)",
                            (code, product_id, "base" if code_unit == "sku" else code_unit))
        clear_inventory_cache()
        return True, f"Product '{name}' registered successfully."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Product registration failed: {e}"


def register_supplier(name, contact_phone, company_name=None, email="", *, operation_key=None):
    """Adds a new supplier entry."""
    if not company_name:
        company_name = name
    try:
        name=str(name or "").strip()
        if not name:
            raise ValueError("Enter the supplier name.")
        with get_db(immediate=True) as (conn, cur):
            if _operation(cur,operation_key,{"kind":"supplier-create","name":name,"phone":contact_phone,
                                           "company":company_name,"email":email}):
                return True,"This supplier was already saved."
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


def _validated_codes(cur, codes, base_unit, strip, box, product_id=None):
    allowed = {unit["code"] for unit in unit_options(base_unit, strip, box)}
    result = {}
    for unit, code in codes.items():
        if not str(code or "").strip():
            continue
        if unit not in allowed:
            raise ValueError("Configure the pack size before assigning its barcode.")
        value = require_available_code(cur, code, product_id)
        if value in result.values():
            raise ValueError("Each package size needs its own barcode.")
        result[unit] = value
    return result


def normalize_expiry(value, precision="DAY"):
    text = str(value or "").strip()
    precision = str(precision or "DAY").upper()
    if precision == "MONTH":
        for fmt in ("%m/%Y", "%m-%Y", "%Y-%m", "%Y/%m", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt).date()
                return date(parsed.year, parsed.month, calendar.monthrange(parsed.year, parsed.month)[1]).isoformat(), precision
            except ValueError:
                continue
        raise ValueError("Enter the printed expiry month as MM/YYYY.")
    if precision != "DAY":
        raise ValueError("Choose an expiry day or month.")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat(), precision
        except ValueError:
            continue
    raise ValueError("Enter a valid expiry date (YYYY-MM-DD).")


def _optional_price(value, label):
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Enter a valid {label}.") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > 1_000_000_000:
        raise ValueError(f"Enter a valid {label}.")
    return float(parsed)


def _operation(cur, operation_key, payload):
    if not operation_key:
        return False
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    cur.execute("SELECT request_hash FROM Stock_Operation WHERE operation_key=%s", (operation_key,))
    prior = cur.fetchone()
    if prior:
        if prior[0] != digest:
            raise ValueError("This stock request was already used for different details. Start a new entry.")
        return True
    cur.execute("INSERT INTO Stock_Operation(operation_key,request_hash,created_at) VALUES (%s,%s,%s)",
                (operation_key, digest, business_now().isoformat(timespec="seconds")))
    return False


def _movement(cur, product_id, batch_id, delta, kind, reason="", employee_id=None, operation_key=None):
    if delta:
        cur.execute("INSERT INTO Stock_Movement(product_id,batch_id,quantity_delta,movement_type,reason,employee_id,operation_key,created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (product_id, batch_id, delta, kind, reason, employee_id, operation_key,
                     business_now().isoformat(timespec="seconds")))


def add_batch(prod_id, supp_id, qty, expiry_date, manufacture_date=None, *, unit_code="base",
              lot_number=None, expiry_precision="DAY", cost_price=None, sale_price=None, mrp=None,
              invoice_reference=None, employee_id=None, operation_key=None, stock_status="SELLABLE"):
    """Adds a new stock shipment batch and updates total product stock."""
    try:
        qty = whole_quantity(qty)
        expiry_date, expiry_precision = normalize_expiry(expiry_date, expiry_precision)
        exp_dt = date.fromisoformat(expiry_date)
        if exp_dt < business_date():
            return False, f"Expiry date ({expiry_date}) has already passed! Expired stock cannot be added."
        manufacture_date = str(manufacture_date or "").strip()
        if manufacture_date:
            manufacture_date = normalize_expiry(manufacture_date)[0]
            mfg = date.fromisoformat(manufacture_date)
            if mfg > business_date() or mfg >= exp_dt:
                raise ValueError("Manufacture date must be in the past and before expiry.")
        cost_price = _optional_price(cost_price, "cost per smallest unit")
        sale_price = _optional_price(sale_price, "selling price per smallest unit")
        mrp = _optional_price(mrp, "printed maximum price per smallest unit")
        if sale_price is not None and sale_price <= 0:
            raise ValueError("Selling price must be greater than zero.")
        if mrp is not None and sale_price is not None and sale_price > mrp:
            raise ValueError("Selling price cannot exceed the printed maximum price.")
        if stock_status not in {"SELLABLE", "QUARANTINED", "RECALLED"}:
            raise ValueError("Choose a valid stock condition.")
        with get_db(immediate=True) as (conn, cur):
            qty_base = convert_quantity(prod_id, qty, unit_code, cur)
            payload = {"kind":"receipt", "product":prod_id, "supplier":supp_id, "quantity":qty_base,
                       "expiry":expiry_date, "precision":expiry_precision, "manufacture":manufacture_date,
                       "lot":str(lot_number or "").strip(), "cost":cost_price, "price":sale_price,
                       "mrp":mrp, "invoice":str(invoice_reference or "").strip(), "status":stock_status}
            if _operation(cur, operation_key, payload):
                return True, "This stock entry was already saved. No stock was added twice."
            cur.execute("SELECT is_active,price FROM Products WHERE id=%s", (prod_id,))
            product = cur.fetchone()
            if not product or not product[0]:
                raise ValueError("Choose an active product before receiving stock.")
            if mrp is not None and (sale_price if sale_price is not None else product[1]) > mrp:
                raise ValueError("Selling price cannot exceed the printed maximum price.")
            cur.execute(
                "INSERT INTO Batch "
                "(number_of_product, expiry_date, product_id, supplier_id, quantity, manufacture_Date,lot_number,expiry_precision,"
                "cost_price,sale_price,mrp,invoice_reference,stock_status,received_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (qty_base, expiry_date, prod_id, supp_id, qty_base, manufacture_date,
                 payload["lot"], expiry_precision,cost_price,sale_price,mrp,payload["invoice"],stock_status,business_now().isoformat(timespec="seconds")),
            )
            batch_id = cur.lastrowid
            cur.execute(
                "UPDATE Products SET stock_quantity = stock_quantity + %s WHERE id = %s",
                (qty_base, prod_id),
            )
            _movement(cur,prod_id,batch_id,qty_base,"RECEIPT",payload["invoice"],employee_id,operation_key)
            if operation_key:
                cur.execute("UPDATE Stock_Operation SET batch_id=%s WHERE operation_key=%s", (batch_id,operation_key))
        clear_inventory_cache()
        return True, f"Stock received: {qty_base} smallest units."
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


def product_details(product_id):
    with get_db() as (_conn, cur):
        cur.execute("SELECT id,product_name,price,min_stock,company_name,category,formula,barcode,"
                    "requires_prescription,base_unit,units_per_strip,units_per_box,rack_location,is_active "
                    "FROM Products WHERE id=%s", (product_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Product was not found.")
        keys = ("id","name","price","min_stock","company","category","formula","barcode",
                "requires_prescription","base_unit","units_per_strip","units_per_box","rack_location","is_active")
        result = dict(zip(keys,row))
        cur.execute("SELECT unit_code,code FROM Product_Code WHERE product_id=%s ORDER BY code", (product_id,))
        codes = {}
        for unit,code in cur.fetchall():
            codes.setdefault(unit,code)
        if result["barcode"]:
            codes["base"] = result["barcode"]
        result["unit_barcodes"] = codes
        return result


def update_product(product_id, *, name, price, min_stock=10, company="General", category="General",
                   formula="N/A", barcode=None, requires_prescription=0, base_unit="unit",
                   units_per_strip=1, units_per_box=1, rack_location="Unassigned", is_active=1,
                   unit_barcodes=None, employee_id=None, operation_key=None):
    """Maintain future catalog facts without rewriting existing batch prices."""
    try:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Enter a product name including its strength.")
        price = _optional_price(price,"selling price")
        if price is None or price <= 0:
            raise ValueError("Selling price must be greater than zero.")
        min_stock = whole_quantity(min_stock,allow_zero=True)
        strip,box = whole_quantity(units_per_strip),whole_quantity(units_per_box)
        with get_db(immediate=True) as (_conn,cur):
            if _operation(cur,operation_key,{"kind":"product-update","product":product_id,"name":name,
                          "price":price,"minimum":min_stock,"company":company,"category":category,
                          "formula":formula,"barcode":barcode,"rx":requires_prescription,"base":base_unit,
                          "strip":strip,"box":box,"rack":rack_location,"active":is_active,"codes":unit_barcodes}):
                return True,"These product details were already saved."
            cur.execute("SELECT id FROM Products WHERE id=%s",(product_id,))
            if not cur.fetchone():
                raise ValueError("Product was not found.")
            cur.execute("SELECT id FROM Products WHERE product_name=%s AND id<>%s",(name,product_id))
            if cur.fetchone():
                raise ValueError("Another product already uses this name. Include strength or pack size.")
            codes = dict(unit_barcodes or {})
            if barcode:
                codes.setdefault("base",barcode)
            codes = _validated_codes(cur,codes,base_unit,strip,box,product_id)
            # Legacy aliases remain searchable; never let replacing a mapping
            # accidentally leave an alias pointing at a different medicine.
            barcode = require_available_code(cur,barcode,product_id) or None
            cur.execute("UPDATE Products SET product_name=%s,price=%s,min_stock=%s,company_name=%s,category=%s,"
                        "formula=%s,barcode=%s,requires_prescription=%s,base_unit=%s,units_per_strip=%s,units_per_box=%s,"
                        "rack_location=%s,is_active=%s WHERE id=%s",
                        (name,price,min_stock,company or "General",category,formula or "N/A",barcode,
                         int(bool(requires_prescription)),str(base_unit or "unit").strip(),strip,box,
                         rack_location or "Unassigned",int(bool(is_active)),product_id))
            cur.execute("DELETE FROM Product_Code WHERE product_id=%s",(product_id,))
            for unit,code in codes.items():
                cur.execute("INSERT INTO Product_Code(code,product_id,unit_code) VALUES (%s,%s,%s)",(code,product_id,unit))
            cur.execute("INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES (%s,%s,%s,%s)",
                        (business_now().isoformat(timespec="seconds"),str(employee_id or "system"),"PRODUCT_UPDATED",
                         f"Product {product_id}: {name}; base unit {base_unit}; strip {strip}; box {box}; active {bool(is_active)}"))
        clear_inventory_cache()
        return True,"Product details saved. Existing batch prices and sales history are preserved."
    except Exception as exc:
        return False,str(exc)


def stock_batches(product_id=None, limit=500):
    """Physical stock, including blocked/expired lots, for owner corrections."""
    with get_db() as (_conn,cur):
        where = "WHERE b.product_id=%s " if product_id is not None else ""
        params = (product_id,) if product_id is not None else ()
        cur.execute("SELECT b.id,p.product_name,b.lot_number,b.quantity,b.expiry_date,b.stock_status,p.base_unit,"
                    "COALESCE(b.sale_price,p.price),b.expiry_precision FROM Batch b JOIN Products p ON p.id=b.product_id "
                    + where + "ORDER BY b.expiry_date,b.id LIMIT %s",params+(min(max(int(limit),1),1000),))
        return cur.fetchall()


def set_batch_count(batch_id, counted_quantity, reason, *, employee_id=None, operation_key=None,
                    expected_quantity=None, stock_status=None):
    """Set a counted physical balance with an immutable adjustment record."""
    try:
        count = whole_quantity(counted_quantity,allow_zero=True)
        reason = str(reason or "").strip()
        if len(reason)<3:
            raise ValueError("Enter a short reason for the stock correction.")
        if stock_status is not None and stock_status not in {"SELLABLE","QUARANTINED","RECALLED"}:
            raise ValueError("Choose a valid stock condition.")
        with get_db(immediate=True) as (_conn,cur):
            payload={"kind":"count","batch":batch_id,"count":count,"reason":reason,"status":stock_status,
                     "expected":expected_quantity}
            if _operation(cur,operation_key,payload):
                return True,"This correction was already saved."
            cur.execute("SELECT product_id,quantity,stock_status FROM Batch WHERE id=%s",(batch_id,))
            row=cur.fetchone()
            if not row:
                raise ValueError("The selected stock batch was not found.")
            product_id,old,status=row
            if expected_quantity is not None and int(expected_quantity)!=int(old):
                raise ValueError("Stock changed while you were counting. Refresh and check the quantity again.")
            delta=count-int(old)
            cur.execute("UPDATE Batch SET quantity=%s,stock_status=%s WHERE id=%s",(count,stock_status or status,batch_id))
            cur.execute("UPDATE Products SET stock_quantity=stock_quantity+%s WHERE id=%s AND stock_quantity+%s>=0",
                        (delta,product_id,delta))
            if cur.rowcount!=1:
                raise ValueError("Product and batch totals need reconciliation before this correction.")
            _movement(cur,product_id,batch_id,delta,"ADJUSTMENT",reason,employee_id,operation_key)
            cur.execute("INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES (%s,%s,%s,%s)",
                        (business_now().isoformat(timespec="seconds"),str(employee_id or "system"),"STOCK_CORRECTED",
                         f"Batch {batch_id}: {old} to {count}; {stock_status or status}; {reason}"))
            if operation_key:
                cur.execute("UPDATE Stock_Operation SET batch_id=%s WHERE operation_key=%s",(batch_id,operation_key))
        clear_inventory_cache()
        return True,"Counted stock and condition saved."
    except Exception as exc:
        return False,str(exc)


def get_all_active_batches():
    """Returns all non-expired, sellable batches ordered by FEFO (expiry_date ASC)."""
    try:
        with get_db() as (conn, cur):
            today = business_date().strftime("%Y-%m-%d")
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date >= %s AND b.quantity > 0 AND b.stock_status='SELLABLE' "
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
            today = business_date().strftime("%Y-%m-%d")
            cutoff = (business_date() + timedelta(days=int(days))).strftime("%Y-%m-%d")
            cur.execute(
                "SELECT b.id, p.product_name, s.supplier_name, b.quantity, b.expiry_date "
                "FROM Batch b "
                "JOIN Products p ON b.product_id = p.id "
                "JOIN Supplier s ON b.supplier_id = s.id "
                "WHERE b.expiry_date >= %s AND b.expiry_date <= %s AND b.quantity > 0 AND b.stock_status='SELLABLE' "
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
            today = business_date().strftime("%Y-%m-%d")
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
            from core.inventory_query_service import _STOCK_CTE
            compare = "min_stock" if threshold is None else "%s"
            params = (business_date().isoformat(),) + (() if threshold is None else (whole_quantity(threshold,allow_zero=True),))
            cur.execute(_STOCK_CTE + "SELECT product_name,sellable_stock,min_stock FROM catalog "
                        "WHERE is_active=1 AND sellable_stock<=" + compare + " ORDER BY sellable_stock,product_name", params)
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Low stock fetch error: {e}")
        return []
