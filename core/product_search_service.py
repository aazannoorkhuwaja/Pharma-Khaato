"""Bounded pharmacy search with explicit packages and batch pricing."""
import re
from datetime import date

from core.business_time import business_date
from core.db_engine import get_db
from core.logger import get_logger
from core.unit_service import code_matches, unit_options

logger = get_logger("PharmaKhaatoProductSearch")
_MAX_RESULTS = 40
_COLUMNS = (
    "p.id,p.product_name,COALESCE(b.sale_price,p.price),b.id,"
    "(SELECT COALESCE(SUM(bs.quantity),0) FROM Batch bs WHERE bs.product_id=p.id "
    "AND bs.quantity>0 AND bs.expiry_date>=%s AND bs.stock_status='SELLABLE'),"
    "b.expiry_date,p.base_unit,p.units_per_strip,p.units_per_box,p.rack_location,"
    "b.lot_number,b.quantity,b.mrp,p.requires_prescription,p.strength,p.dosage_form"
)
_FROM = (
    "Products p JOIN Batch b ON b.id=(SELECT bx.id FROM Batch bx "
    "WHERE bx.product_id=p.id AND bx.quantity>0 AND bx.expiry_date>=%s "
    "AND bx.stock_status='SELLABLE' ORDER BY bx.expiry_date,bx.id LIMIT 1) "
)


def _present(row, unit_code="base"):
    units = unit_options(row[6], row[7], row[8], row[2])
    selected = next((unit for unit in units if unit["code"] == unit_code), None)
    if selected is None:
        raise ValueError("This barcode's pack size needs correction in Stock & Products.")
    multiplier = selected["multiplier"]
    meta = {
        "unit_code": selected["code"], "unit_label": selected["label"],
        "unit_multiplier": multiplier, "base_unit": row[6] or "unit",
        "base_price": float(row[2]), "base_stock": int(row[4]),
        "units_per_strip": int(row[7] or 1), "units_per_box": int(row[8] or 1),
        "units": units, "rack_location": row[9] or "", "lot_number": row[10] or "",
        "batch_stock": int(row[11]), "mrp": row[12],
        "requires_prescription": bool(row[13]), "strength": row[14] or "", "dosage_form": row[15] or "",
    }
    return (row[0], row[1], selected["price"], row[3], int(row[4]) // multiplier, row[5], meta)


def get_product_by_barcode(code):
    value = str(code or "").strip()
    if not value:
        return None
    today = business_date().isoformat()
    with get_db() as (_conn, cur):
        matches = code_matches(cur, value)
        if len(matches) > 1:
            raise ValueError("This barcode matches more than one product. Ask the owner to correct it before selling.")
        if not matches:
            return None
        product_id, unit_code = matches[0]
        cur.execute("SELECT " + _COLUMNS + " FROM " + _FROM + "WHERE p.is_active=1 AND p.id=%s",
                    (today, today, product_id))
        row = cur.fetchone()
    return _present(row, unit_code) if row else None


def _fts_query(term):
    return " ".join(f"{token}*" for token in re.findall(r"[A-Za-z0-9]+", term)[:8])


def search_sellable_products(term):
    raw = str(term or "").strip()
    if not raw:
        return []
    exact = get_product_by_barcode(raw)
    if exact:
        return [exact]
    today = business_date().isoformat()
    query = _fts_query(raw)
    with get_db() as (_conn, cur):
        if query:
            cur.execute("SELECT " + _COLUMNS + " FROM " + _FROM +
                        "JOIN product_fts f ON p.id=CAST(f.product_id AS INTEGER) "
                        "WHERE product_fts MATCH %s AND p.is_active=1 "
                        "ORDER BY bm25(product_fts),p.product_name LIMIT %s",
                        (today,today,query,_MAX_RESULTS))
            rows = cur.fetchall()
            if rows:
                return [_present(row) for row in rows]
        safe = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{safe}%"
        cur.execute("SELECT " + _COLUMNS + " FROM " + _FROM +
                    "WHERE p.is_active=1 AND (p.product_name LIKE %s ESCAPE '\\' "
                    "OR p.formula LIKE %s ESCAPE '\\' OR p.generic_name LIKE %s ESCAPE '\\') "
                    "ORDER BY p.product_name LIMIT %s",
                    (today,today,like,like,like,_MAX_RESULTS))
        return [_present(row) for row in cur.fetchall()]
