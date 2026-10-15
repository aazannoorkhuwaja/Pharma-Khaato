"""Durable settlement of existing customer-credit balances."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from core.db_engine import get_db
from core.logger import get_logger
from core.permission_service import require_permission

logger = get_logger("PharmaKhaatoCreditPayments")

_ALLOWED_METHODS = {
    "cash": "Cash",
    "card": "Credit Card",
    "credit card": "Credit Card",
    "easypaisa": "Easypaisa",
    "jazzcash": "JazzCash",
}


def record_credit_payment(ledger_id, amount, employee_id, payment_method="Cash", note=""):
    """Record a repayment atomically and preserve tender/shift history.

    The remaining-balance read, cash-shift lookup, ledger update and payment
    history insert are serialized under one SQLite write transaction. This
    prevents two simultaneous collection attempts from both approving against
    the same stale balance and over-collecting the customer.
    """
    try:
        ledger_id = int(ledger_id)
        employee_id = int(employee_id)
        amount_dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (TypeError, ValueError):
        return False, "Invalid payment information."
    if amount_dec <= Decimal("0.00"):
        return False, "Payment amount must be greater than zero."

    allowed, reason = require_permission(employee_id, "credit.collect")
    if not allowed:
        return False, reason

    method = _ALLOWED_METHODS.get(str(payment_method or "Cash").strip().lower())
    if method is None:
        return False, "Choose Cash, Card, Easypaisa, or JazzCash."

    try:
        session_id = None
        customer_ref = None
        with get_db() as (_conn, cur):
            # Acquire the write lock before reading amount_due so another
            # repayment cannot validate against the same pre-update balance.
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                "SELECT amount_due, amount_paid, customer_id FROM Customer_Khatoo WHERE id = %s",
                (ledger_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("This customer-credit entry no longer exists.")

            due_dec = Decimal(str(row[0] or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            paid_dec = Decimal(str(row[1] or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            customer_ref = row[2]
            if due_dec <= Decimal("0.00"):
                raise ValueError("This balance has already been cleared.")
            if amount_dec > due_dec:
                raise ValueError(f"Payment exceeds the remaining balance of Rs. {due_dec:.2f}.")

            if method == "Cash":
                cur.execute(
                    "SELECT id FROM Cash_Register_Session "
                    "WHERE employee_id = %s AND status = 'OPEN' ORDER BY id DESC LIMIT 1",
                    (employee_id,),
                )
                session = cur.fetchone()
                if not session:
                    raise ValueError("Start a cash shift before accepting a cash credit payment.")
                session_id = int(session[0])

            paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "UPDATE Customer_Khatoo SET amount_paid = %s, amount_due = %s "
                "WHERE id = %s AND amount_due = %s AND amount_paid = %s",
                (
                    float(paid_dec + amount_dec),
                    float(due_dec - amount_dec),
                    ledger_id,
                    float(due_dec),
                    float(paid_dec),
                ),
            )
            if cur.rowcount != 1:
                raise ValueError(
                    "This customer balance changed while the payment was being recorded. Refresh and try again."
                )
            cur.execute(
                "INSERT INTO Credit_Payment "
                "(khatoo_id, customer_id, employee_id, session_id, amount, payment_method, paid_at, note) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    ledger_id,
                    customer_ref,
                    employee_id,
                    session_id,
                    float(amount_dec),
                    method,
                    paid_at,
                    str(note or "").strip()[:250],
                ),
            )

        try:
            from core.audit_service import log_audit_event
            log_audit_event(
                employee_id,
                "CUSTOMER_CREDIT_PAYMENT",
                f"Recorded {method} customer-credit payment Rs.{amount_dec:.2f}.",
            )
        except Exception as audit_exc:
            logger.warning("Credit-payment audit notice: %s", audit_exc)
        return True, f"Payment of Rs. {amount_dec:.2f} recorded."
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Credit payment failed: %s", exc)
        return False, "The payment could not be recorded. Please try again."


def recent_credit_payments(limit=100):
    safe_limit = max(1, min(int(limit), 500))
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT cp.id, cp.khatoo_id, cp.amount, cp.payment_method, cp.paid_at, "
                "       e.username, cp.note "
                "FROM Credit_Payment cp JOIN Employee e ON e.Employee_id = cp.employee_id "
                "ORDER BY cp.id DESC " + f"LIMIT {safe_limit}"
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Credit payment history failed: %s", exc)
        return []
