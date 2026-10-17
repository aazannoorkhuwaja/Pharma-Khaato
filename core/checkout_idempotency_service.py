"""Explicit, transaction-coupled identity for every checkout submission."""
from __future__ import annotations
from core.business_time import business_date, business_now
import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from core.db_engine import get_db


def _clean_token(token):
    value = str(token or "").strip()
    return value if 0 < len(value) <= 80 and all(c.isalnum() or c in "-_" for c in value) else ""


def request_fingerprint(request):
    from core.pos_service import _normalize_payment_method
    def money(value):
        d = Decimal(str(value))
        if not d.is_finite():
            raise ValueError("Enter a valid finite amount.")
        return format(d.quantize(Decimal("0.01")), ".2f")
    cart = [{"product": str(i.get("prod_id", i.get("id"))),
             "batch": str(i.get("batch_id") or ""),
             "qty": str(i.get("qty")), "price": money(i.get("price", 0)),
             "unit": str(i.get("unit_code", "base")),
             "multiplier": str(i.get("unit_multiplier", 1))} for i in request.cart]
    payload = {"employee": int(request.employee_id), "customer": str(request.customer_id or "WALKIN"),
               "cart": cart, "discount": money(request.discount),
               "tender": _normalize_payment_method(request.payment_method)[0],
               "cash_received": None if request.cash_received is None else money(request.cash_received),
               "expected_total": None if request.expected_total is None else money(request.expected_total),
               "hold": request.held_sale_id, "terminal": request.terminal_id}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _result_from_purchase(cur, purchase_id, duplicate=False):
    from core.pos_service import CheckoutResult
    cur.execute("SELECT total_price,price_with_tax,discount_amount,payment_method,cash_received,change_due,"
                "COALESCE(total_tax,price_with_tax-total_price) FROM Purchase WHERE id=%s", (purchase_id,))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("The checkout safety record does not match a saved sale.")
    return CheckoutResult(True, f"Sale #{purchase_id} completed." + (" Duplicate submission prevented." if duplicate else ""),
                          purchase_id=int(purchase_id), net_total=float(row[0]), total=float(row[1]),
                          discount=float(row[2]), payment_method=row[3], cash_received=row[4],
                          change_due=float(row[5] or 0), total_tax=float(row[6] or 0),
                          outcome="completed", duplicate=duplicate)


def claim_checkout(cur, request):
    """Called only while the sale owns its write transaction. Return saved result or None."""
    token = _clean_token(request.checkout_token)
    if not token:
        raise ValueError("Invalid checkout request token.")
    fingerprint = request_fingerprint(request)
    cur.execute("SELECT employee_id,status,purchase_id,request_fingerprint FROM Checkout_Request WHERE token=%s", (token,))
    row = cur.fetchone()
    if row:
        if int(row[0]) != int(request.employee_id):
            raise ValueError("Checkout request belongs to another staff member.")
        if row[3] and row[3] != fingerprint:
            raise ValueError("This checkout request was already used for a different sale. Restore the original sale or start a new sale.")
        if row[1] == "COMPLETED" and row[2] is not None:
            return _result_from_purchase(cur, row[2], True)
        if row[1] == "CANCELLED":
            raise ValueError("Checkout request was cancelled. Start a new sale.")
        cur.execute("UPDATE Checkout_Request SET request_fingerprint=%s WHERE token=%s", (fingerprint, token))
    else:
        now = business_now().isoformat(timespec="microseconds")
        cur.execute("INSERT INTO Checkout_Request(token,employee_id,status,created_at,updated_at,request_fingerprint) "
                    "VALUES(%s,%s,'PENDING',%s,%s,%s)", (token, request.employee_id, now, now, fingerprint))
    return None


def lookup_checkout_result(token, employee_id=None):
    """None means definitely uncommitted; database errors propagate as unknown outcome."""
    token = _clean_token(token)
    if not token:
        raise ValueError("Invalid checkout request token.")
    with get_db() as (_conn, cur):
        cur.execute("SELECT employee_id,purchase_id,status FROM Checkout_Request WHERE token=%s", (token,))
        row = cur.fetchone()
        if row and employee_id is not None and int(row[0]) != int(employee_id):
            raise ValueError("Checkout request belongs to another staff member.")
        if row and row[2] == "COMPLETED" and row[1] is not None:
            return _result_from_purchase(cur, row[1], True)
    return None


def completed_purchase(token):
    result = lookup_checkout_result(token)
    return result.purchase_id if result else None


def prepare_checkout(token, employee_id):
    """Compatibility preparation; never cancels another terminal's live operation."""
    token = _clean_token(token)
    if not token:
        return False, "Invalid checkout request token.", None
    try:
        employee_id = int(employee_id)
        with get_db(immediate=True) as (_conn, cur):
            cur.execute("SELECT employee_id,status,purchase_id FROM Checkout_Request WHERE token=%s", (token,))
            row = cur.fetchone()
            if row:
                if int(row[0]) != employee_id:
                    return False, "Checkout request belongs to another staff member.", None
                return row[1] != "CANCELLED", row[1], row[2]
            now = business_now().isoformat(timespec="microseconds")
            cur.execute("INSERT INTO Checkout_Request(token,employee_id,status,created_at,updated_at) VALUES(%s,%s,'PENDING',%s,%s)",
                        (token, employee_id, now, now))
        return True, "PENDING", None
    except (TypeError, ValueError):
        return False, "Invalid employee for checkout request.", None


def process_checkout_idempotently(request, process_callable):
    """The engine claims the explicit operation inside its transaction, including concurrent retries."""
    return process_callable(request)
