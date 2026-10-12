"""Durable protection against duplicate POS checkout submissions."""

from __future__ import annotations

from datetime import datetime

from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoCheckoutIdempotency")


def _clean_token(token) -> str:
    value = str(token or "").strip()
    if not value or len(value) > 80:
        return ""
    if not all(ch.isalnum() or ch in "-_" for ch in value):
        return ""
    return value


def prepare_checkout(token, employee_id: int):
    """Register one active checkout token or return its completed purchase.

    Older abandoned PENDING requests for the same employee are cancelled when a
    genuinely new token is prepared. The Purchase trigger completes the active
    token in the same transaction that commits the sale.
    """
    token = _clean_token(token)
    if not token:
        return False, "Invalid checkout request token.", None
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Invalid employee for checkout request.", None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT employee_id, status, purchase_id FROM Checkout_Request WHERE token = %s",
                (token,),
            )
            row = cur.fetchone()
            if row:
                if int(row[0]) != employee_id:
                    return False, "Checkout request belongs to another staff member.", None
                if row[1] == "COMPLETED" and row[2] is not None:
                    return True, "COMPLETED", int(row[2])
                if row[1] == "PENDING":
                    cur.execute(
                        "UPDATE Checkout_Request SET updated_at = %s WHERE token = %s",
                        (now, token),
                    )
                    return True, "PENDING", None
                # A cancelled token is never resurrected; the UI must create a
                # fresh token for a new sale attempt.
                return False, "Checkout request was cancelled. Start a new sale.", None

            cur.execute(
                "UPDATE Checkout_Request SET status = 'CANCELLED', updated_at = %s "
                "WHERE employee_id = %s AND status = 'PENDING'",
                (now, employee_id),
            )
            cur.execute(
                "INSERT INTO Checkout_Request "
                "(token, employee_id, status, purchase_id, created_at, updated_at) "
                "VALUES (%s, %s, 'PENDING', NULL, %s, %s)",
                (token, employee_id, now, now),
            )
        return True, "PENDING", None
    except Exception as exc:
        logger.error("Could not prepare checkout token: %s", exc)
        return False, "Checkout safety record could not be prepared. Please try again.", None


def completed_purchase(token):
    token = _clean_token(token)
    if not token:
        return None
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT purchase_id FROM Checkout_Request "
                "WHERE token = %s AND status = 'COMPLETED' AND purchase_id IS NOT NULL",
                (token,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
    except Exception as exc:
        logger.warning("Checkout completion lookup failed: %s", exc)
        return None


def process_checkout_idempotently(request, process_callable):
    """Run ``process_callable`` at most once for a request token.

    The callable is normally POSModel.process_checkout. A retry after a commit
    returns the original purchase number without writing stock/cash/credit a
    second time.
    """
    token = _clean_token(getattr(request, "checkout_token", None))
    if not token:
        return process_callable(request)

    ok, status, purchase_id = prepare_checkout(token, request.employee_id)
    if not ok:
        from core.pos_service import CheckoutResult
        return CheckoutResult(False, status)
    if status == "COMPLETED" and purchase_id is not None:
        from core.pos_service import CheckoutResult
        return CheckoutResult(
            True,
            f"Sale #{purchase_id} was already completed. Duplicate submission prevented.",
            purchase_id=purchase_id,
        )

    result = process_callable(request)
    if getattr(result, "success", False):
        durable_id = completed_purchase(token)
        if durable_id is None:
            # The sale result says success but its idempotency record was not
            # completed. Do not pretend the safety contract succeeded.
            logger.error("Sale succeeded but checkout token %s was not completed", token)
        elif getattr(result, "purchase_id", None) is None:
            result.purchase_id = durable_id
    return result
