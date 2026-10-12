"""
authorize_manager — service-layer manager authorization for sensitive actions
(high discounts, voids, returns beyond policy).

Uses the existing PBKDF2 password store (no separate PIN column needed):
a manager re-enters THEIR OWN credentials to authorize. Occupation must be
Admin or Manager. Every attempt is audit logged, success or failure.
"""

from core.auth_service import _verify_password
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

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id, First_name, Last_name, occupation, password "
                "FROM Employee WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
    except Exception as e:
        logger.error(f"Manager auth lookup failed: {e}")
        return None, "Authorization lookup failed."

    if not row:
        return None, "Unknown user."
    emp_id, fname, lname, occupation, stored_pw = row

    if str(occupation) not in MANAGER_OCCUPATIONS:
        return None, f"'{username}' ({occupation}) is not authorized to approve."

    if not _verify_password(password, stored_pw):
        return None, "Invalid credentials."

    return emp_id, f"{fname} {lname}".strip()


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
