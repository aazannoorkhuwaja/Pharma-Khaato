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
    "b.quantity,"
    "b.expiry_date,p.base_unit,p.units_per_strip,p.units_per_box,p.rack_location,"
    "b.lot_number,b.quantity,b.mrp,p.requires_prescription,p.strength,p.dosage_form"
)
_FROM = (
    "Products p JOIN Batch b ON b.product_id=p.id AND b.quantity>0 "
    "AND b.expiry_date>=%s AND b.stock_status='SELLABLE' "
)


def _valid_rows(rows):
    """Legacy malformed expiry must not appear as sellable stock."""
    valid = []
    for row in rows:
        try:
            if date.fromisoformat(str(row[5])).isoformat() == str(row[5]):
                valid.append(row)
        except ValueError:
            continue
    return valid



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
        cur.execute("SELECT " + _COLUMNS + " FROM " + _FROM + "WHERE p.is_active=1 AND p.id=%s ORDER BY b.expiry_date,b.id LIMIT %s",
                    (today, product_id, _MAX_RESULTS))
        rows = _valid_rows(cur.fetchall())
    choices = [_present(row, unit_code) for row in rows]
    if not choices:
        return None
    first = choices[0]
    return (*first[:6], {**first[6], "batch_choices": choices})


def _fts_query(term):
    return " ".join(f"{token}*" for token in re.findall(r"[A-Za-z0-9]+", term)[:8])


def search_sellable_products(term):
    raw = str(term or "").strip()
    if not raw:
        return []
    exact = get_product_by_barcode(raw)
    if exact:
        return exact[6].get("batch_choices", [exact])
    today = business_date().isoformat()
    query = _fts_query(raw)
    with get_db() as (_conn, cur):
        if query:
            cur.execute("SELECT " + _COLUMNS + " FROM " + _FROM +
                        "JOIN product_fts f ON p.id=CAST(f.product_id AS INTEGER) "
                        "WHERE product_fts MATCH %s AND p.is_active=1 "
                        "ORDER BY bm25(product_fts),p.product_name,b.expiry_date,b.id LIMIT %s",
                        (today,query,_MAX_RESULTS))
            rows = _valid_rows(cur.fetchall())
            if rows:
                return [_present(row) for row in rows]
        safe = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{safe}%"
        cur.execute("SELECT " + _COLUMNS + " FROM " + _FROM +
                    "WHERE p.is_active=1 AND (p.product_name LIKE %s ESCAPE '\\' "
                    "OR p.formula LIKE %s ESCAPE '\\' OR p.generic_name LIKE %s ESCAPE '\\') "
                    "ORDER BY p.product_name,b.expiry_date,b.id LIMIT %s",
                    (today,like,like,like,_MAX_RESULTS))
        return [_present(row) for row in _valid_rows(cur.fetchall())]
