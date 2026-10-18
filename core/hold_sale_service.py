from core.business_time import business_date, business_now
"""Crash-safe held-sale lifecycle for the POS counter."""

import json
from datetime import datetime

from core.db_engine import get_db
from core.logger import get_logger
from core.permission_service import require_permission

logger = get_logger("PharmaKhaatoHoldSale")

# A RESUMED row means a cashier has loaded it into the active cart. If the
# process dies before checkout/re-hold, that state is stale. Recover those rows
# once per fresh process so a crash cannot permanently hide a held sale.
_RECOVERED_STALE_RESUMES = False
_RECOVERED_PATHS = set()


def _now() -> str:
    return business_now().strftime("%Y-%m-%d %H:%M:%S")


def _recover_stale_resumes_once() -> None:
    global _RECOVERED_STALE_RESUMES
    from core.path_manager import PathManager
    path = PathManager.get_db_path()
    if _RECOVERED_STALE_RESUMES and path in _RECOVERED_PATHS:
        return
    try:
        with get_db(immediate=True) as (_conn, cur):
            cur.execute(
                "UPDATE Hold_Sales SET status = 'HELD', updated_at = %s "
                "WHERE status = 'RESUMED' AND purchase_id IS NULL",
                (_now(),),
            )
        _RECOVERED_STALE_RESUMES = True
        _RECOVERED_PATHS.add(path)
    except Exception as exc:
        logger.warning("Held-sale recovery could not run: %s", exc)


def _draft_payload(customer_id, cart, draft=None):
    payload = dict(draft or {})
    payload.update(customer_id=str(customer_id or "WALKIN"), cart=cart)
    return json.dumps({key: payload[key] for key in (
        "customer_id", "cart", "selected_customer", "customer", "discount", "payment_method", "cash_received"
    ) if key in payload}, separators=(",", ":"), allow_nan=False)


def hold_sale(customer_id, employee_id, cart, note="", *, draft=None):
    """Persist a new held sale without reserving inventory."""
    if not cart:
        return False, "Add at least one item before holding the sale."
    try:
        employee_id = int(employee_id)
    except (ValueError, TypeError):
        return False, "Your staff account could not be verified. Sign in again."

    allowed, reason = require_permission(employee_id, "pos.hold")
    if not allowed:
        return False, reason

    try:
        now_str = _now()
        cart_json = json.dumps(cart, separators=(",", ":"))
        draft_json = _draft_payload(customer_id, cart, draft)
        with get_db(immediate=True) as (_conn, cur):
            cur.execute(
                "INSERT INTO Hold_Sales "
                "(hold_time, customer_id, employee_id, cart_json, note, status, updated_at, draft_json) "
                "VALUES (%s, %s, %s, %s, %s, 'HELD', %s, %s)",
                (
                    now_str,
                    str(customer_id or "WALKIN"),
                    employee_id,
                    cart_json,
                    str(note or "").strip()[:250],
                    now_str,
                    draft_json,
                ),
            )
            hold_id = cur.lastrowid
        logger.info("Held sale %s created by employee %s", hold_id, employee_id)
        return True, hold_id
    except Exception as exc:
        logger.error("Hold sale error: %s", exc)
        return False, "The sale could not be held. Please try again."


def get_held_sales(employee_id=None, limit=100):
    """Return currently available holds, bounded for fast dialog loading."""
    _recover_stale_resumes_once()
    safe_limit = max(1, min(int(limit), 250))

    if employee_id is not None:
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return []
        allowed, _ = require_permission(employee_id, "pos.hold")
        if not allowed:
            return []

    try:
        with get_db(immediate=True) as (_conn, cur):
            if employee_id is None:
                cur.execute(
                    "SELECT id, hold_time, customer_id, employee_id, cart_json, note "
                    "FROM Hold_Sales WHERE status = 'HELD' "
                    "ORDER BY id DESC " + f"LIMIT {safe_limit}"
                )
            else:
                cur.execute(
                    "SELECT id, hold_time, customer_id, employee_id, cart_json, note "
                    "FROM Hold_Sales WHERE status = 'HELD' AND employee_id = %s "
                    "ORDER BY id DESC " + f"LIMIT {safe_limit}",
                    (employee_id,),
                )
            return cur.fetchall()
    except Exception as exc:
        logger.error("Get held sales error: %s", exc)
        return []


def recall_sale(hold_id, employee_id):
    """Mark a hold RESUMED but keep its durable payload until completion."""
    try:
        hold_id = int(hold_id)
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Invalid held sale."

    allowed, reason = require_permission(employee_id, "pos.hold")
    if not allowed:
        return False, reason

    try:
        with get_db(immediate=True) as (_conn, cur):
            cur.execute(
                "SELECT customer_id, cart_json, note, employee_id, status, draft_json "
                "FROM Hold_Sales WHERE id = %s",
                (hold_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("This held sale no longer exists.")
            customer_id, cart_json, note, owner_id, status, draft_json = row
            if int(owner_id) != employee_id:
                raise ValueError("This held sale belongs to another staff member.")
            if status != "HELD":
                raise ValueError("This held sale is already being resumed or has been completed.")

            cart = json.loads(cart_json)
            draft = json.loads(draft_json) if draft_json else {"cart": cart, "customer_id": customer_id}
            now_str = _now()
            cur.execute(
                "UPDATE Hold_Sales SET status = 'RESUMED', resumed_at = %s, updated_at = %s "
                "WHERE id = %s AND status = 'HELD'",
                (now_str, now_str, hold_id),
            )
            if cur.rowcount == 0:
                raise ValueError("This held sale changed before it could be resumed. Try again.")

        return True, {
            "hold_id": hold_id,
            "customer_id": customer_id,
            "cart": cart,
            "note": note,
            "draft": draft,
        }
    except (ValueError, json.JSONDecodeError) as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Recall held sale error: %s", exc)
        return False, "The held sale could not be resumed. Please try again."


def rehold_sale(hold_id, customer_id, employee_id, cart, note="", *, draft=None):
    """Put a resumed cart back into the held queue without creating a duplicate."""
    if not cart:
        return False, "Cannot hold an empty sale."
    try:
        hold_id = int(hold_id)
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Invalid held sale."

    allowed, reason = require_permission(employee_id, "pos.hold")
    if not allowed:
        return False, reason

    try:
        cart_json = json.dumps(cart, separators=(",", ":"))
        draft_json = _draft_payload(customer_id, cart, draft)
        now_str = _now()
        with get_db(immediate=True) as (_conn, cur):
            cur.execute(
                "UPDATE Hold_Sales SET customer_id = %s, employee_id = %s, cart_json = %s, "
                "note = %s, status = 'HELD', resumed_at = NULL, updated_at = %s, draft_json = %s "
                "WHERE id = %s AND status = 'RESUMED' AND employee_id = %s",
                (
                    str(customer_id or "WALKIN"),
                    employee_id,
                    cart_json,
                    str(note or "").strip()[:250],
                    now_str,
                    draft_json,
                    hold_id,
                    employee_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("The resumed held sale could not be found.")
        return True, hold_id
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Re-hold sale error: %s", exc)
        return False, "The sale could not be held again. Please try again."


def complete_hold(hold_id, employee_id, purchase_id=None):
    """Mark a resumed hold completed only after its checkout committed."""
    try:
        hold_id = int(hold_id)
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Invalid held sale."

    try:
        now_str = _now()
        with get_db() as (_conn, cur):
            cur.execute(
                "UPDATE Hold_Sales SET status = 'COMPLETED', completed_at = %s, updated_at = %s, "
                "note = CASE WHEN %s IS NULL THEN note ELSE trim(COALESCE(note,'') || ' Completed as sale #' || %s) END "
                "WHERE id = %s AND employee_id = %s AND status = 'RESUMED'",
                (now_str, now_str, purchase_id, purchase_id, hold_id, employee_id),
            )
            if cur.rowcount == 0:
                return False, "The held sale was not in a resumable state."
        return True, "Held sale completed."
    except Exception as exc:
        logger.error("Complete held sale error: %s", exc)
        return False, "The sale completed, but its held-sale status could not be updated."


def cancel_hold(hold_id, employee_id):
    """Soft-cancel a held sale while keeping audit history."""
    try:
        hold_id = int(hold_id)
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Invalid held sale."
    allowed, reason = require_permission(employee_id, "pos.hold")
    if not allowed:
        return False, reason
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "UPDATE Hold_Sales SET status = 'CANCELLED', updated_at = %s "
                "WHERE id = %s AND employee_id = %s AND status IN ('HELD','RESUMED')",
                (_now(), hold_id, employee_id),
            )
            if cur.rowcount == 0:
                return False, "This held sale could not be cancelled."
        return True, "Held sale cancelled."
    except Exception as exc:
        logger.error("Cancel held sale error: %s", exc)
        return False, "The held sale could not be cancelled."
