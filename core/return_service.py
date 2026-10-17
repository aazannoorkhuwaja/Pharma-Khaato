"""Auditable, tender-aware customer returns and refunds.

The UI supplies only purchase/batch IDs, quantities, reason, and stock condition.
Prices, sold quantities, prior returns, payment tender, and credit state are
re-read from SQLite inside the transaction so callers cannot forge refund data.
"""

from __future__ import annotations

import sqlite3
import threading
import hashlib
import json
from core.business_time import business_date, business_now
from decimal import Decimal, ROUND_HALF_UP

from core.db_engine import get_db
from core.inventory_service import clear_inventory_cache
from core.logger import get_logger
from core.permission_service import require_permission

logger = get_logger("PharmaKhaatoReturns")
_RETURN_LOCK = threading.Lock()
_CENT = Decimal("0.01")


def lookup_return_result(operation_id, employee_id):
    """None means no committed return under this identity; DB errors propagate."""
    with get_db() as (_conn, cur):
        cur.execute("SELECT employee_id,result_json FROM Return_Operation WHERE operation_id=%s", (str(operation_id),))
        row = cur.fetchone()
        if row is None:
            return None
        if int(row[0]) != int(employee_id):
            raise ValueError("That return belongs to another staff member.")
        return json.loads(row[1])


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _canonical_tender(value: str) -> str:
    key = str(value or "Cash").strip().lower()
    if key in {"cash", ""}:
        return "Cash"
    if key in {"credit card", "card"}:
        return "Credit Card"
    if key == "easypaisa":
        return "Easypaisa"
    if key == "jazzcash":
        return "JazzCash"
    if "khatoo" in key or key in {"credit", "credit (khatoo)"}:
        return "Khatoo Credit"
    return str(value or "Other").strip()


def _active_cash_session(cur, employee_id: int) -> int | None:
    cur.execute(
        "SELECT id FROM Cash_Register_Session "
        "WHERE employee_id = %s AND status = 'OPEN' ORDER BY id DESC LIMIT 1",
        (employee_id,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def _sale_header(cur, purchase_id: int):
    cur.execute(
        "SELECT p.id, p.customer_id, p.payment_method, p.price_with_tax, "
        "       p.discount_amount, r.printing_date, r.time, "
        "       COALESCE(c.first_name || ' ' || c.last_name, 'Walk-in Customer') "
        "FROM Purchase p "
        "JOIN Receipt r ON r.purchase_id = p.id "
        "LEFT JOIN Customers c ON c.id_card_number = p.customer_id "
        "WHERE p.id = %s",
        (purchase_id,),
    )
    return cur.fetchone()


def _sale_lines(cur, purchase_id: int):
    cur.execute(
        "SELECT sd.batch_id, b.product_id, p.product_name, sd.Quantity, "
        "       COALESCE(sd.unit_price, p.price), "
        "       COALESCE(sd.line_subtotal, sd.Quantity * COALESCE(sd.unit_price, p.price)), "
        "       b.expiry_date, "
        "       COALESCE((SELECT SUM(ri.quantity) "
        "                 FROM Return_Items ri "
        "                 JOIN Customer_Returns cr ON cr.id = ri.return_id "
        "                 WHERE cr.purchase_id = sd.purchase_id "
        "                   AND ri.batch_id = sd.batch_id), 0) "
        "FROM Sales_details sd "
        "JOIN Batch b ON b.id = sd.batch_id "
        "JOIN Products p ON p.id = b.product_id "
        "WHERE sd.purchase_id = %s ORDER BY sd.batch_id",
        (purchase_id,),
    )
    return cur.fetchall()


def get_returnable_sale(purchase_id: int):
    """Return a compact indexed read model for the Returns screen."""
    try:
        purchase_id = int(purchase_id)
    except (TypeError, ValueError):
        return None

    try:
        with get_db() as (_conn, cur):
            header = _sale_header(cur, purchase_id)
            if not header:
                return None
            lines = _sale_lines(cur, purchase_id)
            cur.execute(
                "SELECT COALESCE(SUM(refund_amount), 0) FROM Customer_Returns WHERE purchase_id = %s",
                (purchase_id,),
            )
            refunded = _money((cur.fetchone() or [0])[0])

        _, customer_id, tender, gross, discount, sale_date, sale_time, customer_name = header
        result_lines = []
        for batch_id, product_id, name, sold_qty, unit_price, line_subtotal, expiry, returned_qty in lines:
            remaining = max(int(sold_qty or 0) - int(returned_qty or 0), 0)
            result_lines.append({
                "batch_id": int(batch_id),
                "product_id": int(product_id),
                "product_name": str(name),
                "sold_qty": int(sold_qty or 0),
                "already_returned": int(returned_qty or 0),
                "remaining_returnable": remaining,
                "unit_price": float(_money(unit_price)),
                "line_base": float(_money(line_subtotal)),
                "expiry_date": str(expiry),
            })
        return {
            "purchase_id": purchase_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "payment_method": _canonical_tender(tender),
            "gross_total": float(_money(gross)),
            "discount": float(_money(discount)),
            "already_refunded": float(refunded),
            "sale_date": str(sale_date),
            "sale_time": str(sale_time),
            "lines": result_lines,
        }
    except Exception as exc:
        logger.error("Returnable sale lookup failed for %s: %s", purchase_id, exc)
        return None


def _allocate_credit_repayment_refunds(
    cur,
    *,
    ledger_id: int,
    excess: Decimal,
    return_id: int,
    employee_id: int,
    now_str: str,
):
    """Reverse prior credit collections by their actual tender, newest first."""
    if excess <= Decimal("0.00"):
        return [], Decimal("0.00")

    cur.execute(
        "SELECT cp.id, cp.amount, cp.payment_method, "
        "       COALESCE((SELECT SUM(rt.amount) FROM Refund_Transaction rt "
        "                 WHERE rt.source_credit_payment_id = cp.id), 0) "
        "       + COALESCE((SELECT SUM(rv.amount) FROM Credit_Payment_Reversal rv "
        "                 WHERE rv.payment_id=cp.id), 0) "
        "FROM Credit_Payment cp WHERE cp.khatoo_id = %s ORDER BY cp.id DESC",
        (ledger_id,),
    )
    payment_rows = cur.fetchall()

    available_total = sum(
        (max(_money(amount) - _money(refunded), Decimal("0.00"))
         for _pid, amount, _method, refunded in payment_rows),
        Decimal("0.00"),
    )
    if available_total < excess:
        raise ValueError(
            "This older credit balance does not have enough tender history for an automatic refund. "
            "Use manual reconciliation instead of guessing the refund method."
        )

    remaining = excess
    refund_rows = []
    cash_session_id = None
    for payment_id, amount, method, already_refunded in payment_rows:
        if remaining <= Decimal("0.00"):
            break
        available = max(_money(amount) - _money(already_refunded), Decimal("0.00"))
        if available <= Decimal("0.00"):
            continue
        refund_amount = min(available, remaining)
        tender = _canonical_tender(method)
        session_id = None
        if tender == "Cash":
            if cash_session_id is None:
                cash_session_id = _active_cash_session(cur, employee_id)
            if cash_session_id is None:
                raise ValueError(
                    "Start a cash shift before refunding a credit payment that was originally paid in cash."
                )
            session_id = cash_session_id
            cur.execute(
                "INSERT INTO Cash_Movement "
                "(session_id, employee_id, movement_type, amount, reason, created_at) "
                "VALUES (%s, %s, 'REFUND', %s, %s, %s)",
                (
                    session_id,
                    employee_id,
                    float(refund_amount),
                    f"Customer-credit return refund #{return_id}",
                    now_str,
                ),
            )

        cur.execute(
            "INSERT INTO Refund_Transaction "
            "(return_id, employee_id, session_id, source_credit_payment_id, amount, payment_method, created_at, note) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                return_id,
                employee_id,
                session_id,
                payment_id,
                float(refund_amount),
                tender,
                now_str,
                "Refund of previously collected customer credit",
            ),
        )
        refund_rows.append((tender, float(refund_amount)))
        remaining -= refund_amount

    return refund_rows, cash_session_id


def process_return(
    purchase_id: int,
    requested_items: list,
    employee_id: int,
    reason: str = "Customer return",
    condition: str = "SELLABLE",
    operation_id: str | None = None,
):
    """Process a return atomically using authoritative sale data.

    ``requested_items`` contains only ``batch_id`` and ``qty``. Any UI-supplied
    price/product fields are intentionally ignored.
    """
    try:
        purchase_id = int(purchase_id)
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Invalid return information."
    if not requested_items:
        return False, "Select at least one item to return."

    allowed, permission_reason = require_permission(employee_id, "returns.process")
    if not allowed:
        return False, permission_reason

    condition = str(condition or "SELLABLE").strip().upper()
    if condition not in {"SELLABLE", "DAMAGED", "OPENED", "QUARANTINE"}:
        return False, "Choose a valid return condition."

    # Consolidate repeated batch rows before entering the transaction.
    requested_by_batch: dict[int, int] = {}
    try:
        for item in requested_items:
            batch_id = int(item.get("batch_id"))
            raw_qty = Decimal(str(item.get("qty", 0)))
            if not raw_qty.is_finite() or raw_qty != raw_qty.to_integral_value():
                raise ValueError("Return quantities must be whole units.")
            qty = int(raw_qty)
            if qty <= 0:
                continue
            requested_by_batch[batch_id] = requested_by_batch.get(batch_id, 0) + qty
    except (TypeError, ValueError, AttributeError):
        return False, "One or more return quantities are invalid."
    if not requested_by_batch:
        return False, "Select at least one positive return quantity."

    token = str(operation_id or "").strip()
    if token and (len(token) > 100 or not all(c.isalnum() or c in '-_' for c in token)):
        return False, "Invalid return request. Reopen the return and try again."
    fingerprint = hashlib.sha256(json.dumps(
        [purchase_id, employee_id, sorted(requested_by_batch.items()), reason, condition],
        ensure_ascii=False, separators=(',', ':'),
    ).encode()).hexdigest()

    if not _RETURN_LOCK.acquire(blocking=False):
        return False, "Another return is being processed. Try again in a moment."

    return_id = None
    refund_total = Decimal("0.00")
    refund_tenders = []
    try:
        with get_db(immediate=True) as (conn, cur):
            # Serialize validation+write so two return attempts cannot both use
            # the same remaining quantity.
            if token:
                cur.execute("SELECT employee_id,request_hash,result_json FROM Return_Operation WHERE operation_id=%s", (token,))
                previous = cur.fetchone()
                if previous:
                    if previous[0] != employee_id or previous[1] != fingerprint:
                        raise ValueError("This return request belongs to different return details.")
                    return True, json.loads(previous[2])

            header = _sale_header(cur, purchase_id)
            if not header:
                raise ValueError(f"Sale #{purchase_id} was not found.")
            _, customer_id, original_tender_raw, gross_raw, _discount, _sale_date, _sale_time, _customer_name = header
            original_tender = _canonical_tender(original_tender_raw)
            gross_total = _money(gross_raw)

            lines = _sale_lines(cur, purchase_id)
            if not lines:
                raise ValueError("This sale has no returnable line items.")
            line_map = {int(line[0]): line for line in lines}

            original_base = sum((_money(line[5]) for line in lines), Decimal("0.00"))
            if original_base <= Decimal("0.00"):
                raise ValueError("The original sale value cannot be reconstructed safely.")

            requested_base = Decimal("0.00")
            prepared_items = []
            remaining_after = 0
            today = business_date().isoformat()

            for batch_id, line in line_map.items():
                sold_qty = int(line[3] or 0)
                returned_qty = int(line[7] or 0)
                request_qty = requested_by_batch.get(batch_id, 0)
                available = max(sold_qty - returned_qty, 0)
                if request_qty > available:
                    raise ValueError(
                        f"{line[2]} only has {available} unit(s) remaining returnable on this sale."
                    )
                remaining_after += max(available - request_qty, 0)
                if request_qty <= 0:
                    continue

                product_id = int(line[1])
                product_name = str(line[2])
                unit_price = Decimal(str(line[4]))
                expiry_date = str(line[6])
                line_return_base = Decimal(str(line[5])) * request_qty / sold_qty
                requested_base += line_return_base

                cur.execute("SELECT b.stock_status,p.is_active FROM Batch b JOIN Products p ON p.id=b.product_id WHERE b.id=%s", (batch_id,))
                status = cur.fetchone()
                can_restock = condition == "SELLABLE" and expiry_date >= today and status and status[0] == 'SELLABLE' and bool(status[1])
                restock_status = "RESTOCKED" if can_restock else (
                    "EXPIRED_QUARANTINE" if condition == "SELLABLE" and expiry_date < today
                    else f"{condition}_QUARANTINE"
                )
                prepared_items.append({
                    "batch_id": batch_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "qty": request_qty,
                    "unit_price": unit_price,
                    "line_base": line_return_base,
                    "restock": can_restock,
                    "restock_status": restock_status,
                })

            unknown_batches = set(requested_by_batch) - set(line_map)
            if unknown_batches:
                raise ValueError("One or more selected items were not sold on this sale.")
            if not prepared_items:
                raise ValueError("Select at least one returnable item.")

            cur.execute(
                "SELECT COALESCE(SUM(refund_amount), 0) FROM Customer_Returns WHERE purchase_id = %s",
                (purchase_id,),
            )
            already_refunded = _money((cur.fetchone() or [0])[0])
            remaining_refundable = max(gross_total - already_refunded, Decimal("0.00"))

            proportional_refund = (gross_total * requested_base / original_base).quantize(
                _CENT, rounding=ROUND_HALF_UP
            )
            # On the final remaining item(s), absorb any cent-level proportional
            # rounding so total refunds can equal but never exceed the sale gross.
            refund_total = remaining_refundable if remaining_after == 0 else min(proportional_refund, remaining_refundable)
            if refund_total <= Decimal("0.00"):
                raise ValueError("This sale has already been fully refunded.")

            now = business_now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            cur.execute(
                "INSERT INTO Customer_Returns "
                "(purchase_id, customer_id, employee_id, refund_amount, reason, return_date, return_time, "
                " refund_method, session_id, refund_status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, 'RECORDED')",
                (
                    purchase_id,
                    customer_id or "WALKIN",
                    employee_id,
                    float(refund_total),
                    str(reason or "Customer return").strip()[:250],
                    date_str,
                    time_str,
                    original_tender,
                ),
            )
            return_id = cur.lastrowid

            for item in prepared_items:
                # Return_Items subtotal is base merchandise value; Customer_Returns
                # carries the actual post-discount/tax refund amount.
                cur.execute(
                    "INSERT INTO Return_Items "
                    "(return_id, product_id, batch_id, quantity, unit_price, subtotal, restock_status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        return_id,
                        item["product_id"],
                        item["batch_id"],
                        item["qty"],
                        float(item["unit_price"]),
                        float(item["line_base"]),
                        item["restock_status"],
                    ),
                )
                if item["restock"]:
                    cur.execute(
                        "UPDATE Batch SET quantity = quantity + %s WHERE id = %s",
                        (item["qty"], item["batch_id"]),
                    )
                    cur.execute(
                        "UPDATE Products SET stock_quantity = stock_quantity + %s WHERE id = %s",
                        (item["qty"], item["product_id"]),
                    )
                    cur.execute(
                        "INSERT INTO Stock_Movement(product_id,batch_id,quantity_delta,movement_type,reason,employee_id,operation_key,created_at) "
                        "VALUES (%s,%s,%s,'CUSTOMER_RETURN',%s,%s,%s,%s)",
                        (item["product_id"],item["batch_id"],item["qty"],str(reason)[:250],employee_id,token or None,now_str),
                    )

            return_session_id = None
            if original_tender == "Cash":
                return_session_id = _active_cash_session(cur, employee_id)
                if return_session_id is None:
                    raise ValueError("Start a cash shift before paying a cash refund.")
                cur.execute(
                    "INSERT INTO Cash_Movement "
                    "(session_id, employee_id, movement_type, amount, reason, created_at) "
                    "VALUES (%s, %s, 'REFUND', %s, %s, %s)",
                    (
                        return_session_id,
                        employee_id,
                        float(refund_total),
                        f"Sale return #{return_id} for sale #{purchase_id}",
                        now_str,
                    ),
                )
                cur.execute(
                    "INSERT INTO Refund_Transaction "
                    "(return_id, employee_id, session_id, amount, payment_method, created_at, note) "
                    "VALUES (%s, %s, %s, %s, 'Cash', %s, %s)",
                    (
                        return_id,
                        employee_id,
                        return_session_id,
                        float(refund_total),
                        now_str,
                        "Refund to original cash tender",
                    ),
                )
                refund_tenders.append(("Cash", float(refund_total)))

            elif original_tender in {"Credit Card", "Easypaisa", "JazzCash"}:
                cur.execute(
                    "INSERT INTO Refund_Transaction "
                    "(return_id, employee_id, session_id, amount, payment_method, created_at, note) "
                    "VALUES (%s, %s, NULL, %s, %s, %s, %s)",
                    (
                        return_id,
                        employee_id,
                        float(refund_total),
                        original_tender,
                        now_str,
                        "Refund to original digital tender",
                    ),
                )
                refund_tenders.append((original_tender, float(refund_total)))

            elif original_tender == "Khatoo Credit":
                cur.execute(
                    "SELECT id, amount_due, amount_paid FROM Customer_Khatoo "
                    "WHERE purchase_id = %s AND customer_id = %s ORDER BY id DESC LIMIT 1",
                    (purchase_id, customer_id),
                )
                ledger = cur.fetchone()
                if not ledger:
                    raise ValueError("The customer-credit ledger for this sale could not be found.")
                ledger_id = int(ledger[0])
                amount_due = _money(ledger[1])
                amount_paid = _money(ledger[2])

                due_reduction = min(refund_total, amount_due)
                excess_to_customer = refund_total - due_reduction
                new_due = amount_due - due_reduction
                new_paid = amount_paid

                if excess_to_customer > Decimal("0.00"):
                    if excess_to_customer > amount_paid:
                        raise ValueError(
                            "The customer-credit ledger is inconsistent with this refund. "
                            "Use manual reconciliation rather than issuing an uncertain refund."
                        )
                    allocated, cash_session_id = _allocate_credit_repayment_refunds(
                        cur,
                        ledger_id=ledger_id,
                        excess=excess_to_customer,
                        return_id=return_id,
                        employee_id=employee_id,
                        now_str=now_str,
                    )
                    refund_tenders.extend(allocated)
                    if cash_session_id is not None:
                        return_session_id = cash_session_id
                    new_paid = amount_paid - excess_to_customer

                cur.execute(
                    "UPDATE Customer_Khatoo SET amount_due = %s, amount_paid = %s WHERE id = %s",
                    (float(new_due), float(new_paid), ledger_id),
                )
                if due_reduction > Decimal("0.00"):
                    refund_tenders.append(("Customer Credit Reduced", float(due_reduction)))

            else:
                raise ValueError(
                    f"Refund method '{original_tender}' is not configured. Manual reconciliation is required."
                )

            cur.execute(
                "UPDATE Customer_Returns SET session_id = %s WHERE id = %s",
                (return_session_id, return_id),
            )
            result = {"return_id": return_id, "purchase_id": purchase_id,
                      "refund_amount": float(refund_total), "refund_tenders": refund_tenders,
                      "items": len(prepared_items)}
            if token:
                cur.execute(
                    "INSERT INTO Return_Operation(operation_id,employee_id,request_hash,return_id,result_json) VALUES (%s,%s,%s,%s,%s)",
                    (token,employee_id,fingerprint,return_id,json.dumps(result)),
                )

        clear_inventory_cache()
        try:
            from core.audit_service import log_audit_event
            tender_summary = ", ".join(f"{name} Rs.{amount:.2f}" for name, amount in refund_tenders)
            log_audit_event(
                employee_id,
                "SALE_RETURN",
                f"Return #{return_id} for sale #{purchase_id}; refund Rs.{refund_total:.2f}; {tender_summary}.",
            )
        except Exception as audit_exc:
            logger.warning("Return audit notice: %s", audit_exc)

        return True, {
            "return_id": return_id,
            "purchase_id": purchase_id,
            "refund_amount": float(refund_total),
            "refund_tenders": refund_tenders,
            "items": len(prepared_items),
        }
    except ValueError as exc:
        return False, str(exc)
    except (sqlite3.Error, OSError) as exc:
        logger.error("Return database error for sale %s: %s", purchase_id, exc)
        return False, "The return could not be saved. No refund was recorded."
    except Exception as exc:
        logger.exception("Unexpected return failure for sale %s: %s", purchase_id, exc)
        return False, "The return could not be completed safely."
    finally:
        _RETURN_LOCK.release()
