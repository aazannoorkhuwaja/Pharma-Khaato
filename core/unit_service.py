"""Whole-unit pharmacy pack conversions shared by receiving and checkout.

Stock and returns always use the smallest counted unit (tablet, bottle, vial,
etc.). A strip or a box is an explicitly configured number of those units.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.db_engine import get_db


def whole_quantity(value, *, allow_zero=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Enter a whole quantity.") from exc
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError("Quantity must be a whole number.")
    if number < (0 if allow_zero else 1) or number > 1_000_000_000:
        raise ValueError("Quantity is outside the allowed range.")
    return int(number)


def unit_options(base_unit="unit", units_per_strip=1, units_per_box=1, base_price=0):
    base_unit = str(base_unit or "unit").strip()[:30] or "unit"
    strip = whole_quantity(units_per_strip)
    box = whole_quantity(units_per_box)
    if strip > 1 and box > 1 and (box < strip or box % strip):
        raise ValueError("Units in a box must be a whole number of strips.")
    price = Decimal(str(base_price or 0))
    if not price.is_finite() or price < 0:
        raise ValueError("Selling price is invalid.")
    options = [{"code": "base", "label": base_unit, "multiplier": 1}]
    if strip > 1:
        options.append({"code": "strip", "label": f"Strip ({strip} {base_unit}s)", "multiplier": strip})
    if box > 1:
        options.append({"code": "box", "label": f"Box ({box} {base_unit}s)", "multiplier": box})
    for option in options:
        option["price"] = float((price * option["multiplier"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return options


def product_unit_config(product_id, cur=None):
    if cur is None:
        with get_db() as (_conn, cursor):
            return product_unit_config(product_id, cursor)
    cur.execute(
        "SELECT base_unit,units_per_strip,units_per_box,price FROM Products WHERE id=%s",
        (product_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Product was not found.")
    return {"base_unit": row[0] or "unit", "units_per_strip": int(row[1] or 1),
            "units_per_box": int(row[2] or 1), "base_price": float(row[3])}


def get_sell_units(product_id, cur=None, base_price=None):
    config = product_unit_config(product_id, cur)
    return unit_options(config["base_unit"], config["units_per_strip"],
                        config["units_per_box"], config["base_price"] if base_price is None else base_price)


def resolve_unit(product_id, unit_code="base", cur=None, base_price=None):
    for option in get_sell_units(product_id, cur, base_price):
        if option["code"] == str(unit_code or "base"):
            return option
    raise ValueError("This pack size is not configured for the product. Choose a listed unit.")


def convert_quantity(product_id, quantity, unit_code="base", cur=None):
    result = whole_quantity(quantity) * resolve_unit(product_id, unit_code, cur)["multiplier"]
    return whole_quantity(result)


def code_matches(cur, code):
    """Return every code owner, including ambiguous pre-migration records."""
    value = str(code or "").strip()
    if not value:
        return []
    cur.execute(
        "SELECT product_id,unit_code FROM Product_Code WHERE code=%s "
        "UNION SELECT id,'base' FROM Products WHERE barcode=%s OR sku=%s OR alternate_barcode=%s",
        (value, value, value, value),
    )
    rows = cur.fetchall()
    # Legacy product columns represent a code only when no explicit mapping
    # for that same product exists (a box barcode is also the primary barcode).
    explicit = {int(row[0]): row[1] for row in rows if row[1] != "base"}
    return sorted({(int(pid), explicit.get(int(pid), unit)) for pid, unit in rows})


def require_available_code(cur, code, product_id=None):
    value = str(code or "").strip()
    if not value:
        return ""
    if len(value) > 120 or any(ord(char) < 32 for char in value):
        raise ValueError("Barcode is invalid.")
    owners = code_matches(cur, value)
    if any(owner != product_id for owner, _unit in owners):
        raise ValueError(f"Barcode or SKU '{value}' already belongs to another product.")
    return value
