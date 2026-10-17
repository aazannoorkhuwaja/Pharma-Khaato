"""
authorize_manager — service-layer manager authorization for sensitive actions
(high discounts, voids, returns beyond policy).

Uses the existing PBKDF2 password store (no separate PIN column needed):
a manager re-enters THEIR OWN credentials to authorize. Occupation must be
Admin or Manager. Every attempt is audit logged, success or failure.
"""

import hashlib
import secrets
import sqlite3
import time
from decimal import Decimal, ROUND_HALF_UP

from core.auth_service import login_user
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoManagerAuth")

MANAGER_OCCUPATIONS = ("Admin", "Manager", "ADMIN", "MANAGER")
DEFAULT_DISCOUNT_THRESHOLD_PCT = 10.0


def verify_manager(username: str, password: str):
    """
    Returns (manager_employee_id, display_name) when the credentials belong to
    an active Admin/Manager account, else (None, reason).
    Does NOT create a session — authorization only.
    """
    username = str(username).strip()
    if not username or not password:
        return None, "Username and password are required."

    from core.audit_service import log_audit_event
    try:
        row = login_user(username, password)
    except PermissionError as exc:
        log_audit_event(username, "MANAGER_AUTH_FAILED", "Manager approval rate limited.")
        return None, str(exc)
    if not row or str(row[3]).strip().lower() not in {"admin", "manager", "administrator"}:
        log_audit_event(username, "MANAGER_AUTH_FAILED", "Manager approval credentials rejected.")
        return None, "Manager credentials could not be verified."
    emp_id, fname, lname, _role = row
    log_audit_event(emp_id, "MANAGER_AUTH_SUCCESS", "Manager identity verified for approval.")
    return emp_id, f"{fname} {lname}".strip()


def _minor(value):
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if not amount.is_finite() or amount < 0:
        raise ValueError("Enter a valid amount.")
    return int(amount * 100)


def issue_discount_approval(username, password, operator_id, discount_amount, subtotal):
    """Issue an opaque five-minute approval for exactly one cashier/amount pair."""
    from core.permission_service import require_permission
    allowed, message = require_permission(operator_id, "pos.sell")
    if not allowed:
        return None, message
    manager_id, who = verify_manager(username, password)
    if manager_id is None:
        return None, who
    try:
        token = secrets.token_urlsafe(32)
        with get_db(immediate=True) as (_conn, cur):
            cur.execute("DELETE FROM Manager_Approval WHERE expires_at < %s", (time.time() - 86400,))
            cur.execute(
                "INSERT INTO Manager_Approval (token_hash,operator_id,manager_id,subtotal_minor,discount_minor,expires_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (hashlib.sha256(token.encode()).hexdigest(), int(operator_id), manager_id,
                 _minor(subtotal), _minor(discount_amount), time.time() + 300),
            )
        return token, who
    except (ValueError, ArithmeticError, sqlite3.Error):
        return None, "Approval could not be recorded. Try again."


def validate_discount_approval(cur, token, operator_id, discount_amount, subtotal):
    """Consume an amount-bound approval inside the sale's own transaction."""
    if not isinstance(token, str) or len(token) > 200:
        return False, "Manager approval is required for this discount."
    try:
        digest = hashlib.sha256(token.encode()).hexdigest()
        cur.execute("SELECT operator_id,manager_id,subtotal_minor,discount_minor,expires_at,used_at FROM Manager_Approval WHERE token_hash=%s", (digest,))
        row = cur.fetchone()
        if not row or row[5] is not None or float(row[4]) < time.time():
            return False, "Manager approval expired or was already used. Ask for approval again."
        if (int(row[0]), int(row[2]), int(row[3])) != (int(operator_id), _minor(subtotal), _minor(discount_amount)):
            return False, "The cart changed. Ask for manager approval again."
        cur.execute("SELECT occupation FROM Employee WHERE Employee_id=%s", (row[1],))
        manager = cur.fetchone()
        if not manager or str(manager[0]).lower() not in {"admin", "administrator", "manager"}:
            return False, "The approving account is no longer a manager."
        cur.execute("UPDATE Manager_Approval SET used_at=%s WHERE token_hash=%s AND used_at IS NULL", (time.time(), digest))
        cur.execute("INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES(datetime('now','localtime'),%s,'DISCOUNT_APPROVAL_USED',%s)", (str(row[1]), f"Approved cashier {int(operator_id)} discount {_minor(discount_amount)} minor units."))
        return True, "Manager approval accepted."
    except (ValueError, ArithmeticError, sqlite3.Error):
        return False, "Manager approval could not be verified."


def discount_requires_authorization(discount_amount: float, subtotal: float,
                                    threshold_pct: float = DEFAULT_DISCOUNT_THRESHOLD_PCT) -> bool:
    """True when discount exceeds threshold percent of the pre-discount subtotal."""
    try:
        if subtotal <= 0:
            return float(discount_amount) > 0
        pct = (float(discount_amount) / float(subtotal)) * 100.0
        return pct > threshold_pct
    except (TypeError, ValueError, ZeroDivisionError):
        return False


def enforce_discount_policy(discount_amount: float, subtotal: float,
                            manager_username: str = None, manager_password: str = None):
    """
    Service-layer gate. Call before confirm_sale for any cart with a discount.

    Returns (allowed: bool, message: str).
      - Small discounts: allowed without approval.
      - Large discounts require valid manager credentials; result is audited.
    """
    if not discount_requires_authorization(discount_amount, subtotal):
        return True, "Discount within cashier limit."

    if not manager_username:
        return False, (
            "Discount exceeds the cashier limit "
            f"({DEFAULT_DISCOUNT_THRESHOLD_PCT:.0f}%). Manager authorization required."
        )

    emp_id, who = verify_manager(manager_username, manager_password)
    from core.audit_service import log_audit_event
    if emp_id is None:
        log_audit_event(0, "DISCOUNT_AUTH_FAILED",
                        f"Failed manager auth for '{manager_username}' "
                        f"(discount {discount_amount} on {subtotal}).")
        return False, f"Authorization failed: {who}"

    log_audit_event(emp_id, "DISCOUNT_AUTHORIZED",
                    f"{who} authorized discount {discount_amount:.2f} on subtotal {subtotal:.2f}.")
    return True, f"Authorized by {who}."
