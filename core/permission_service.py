"""Central role/action authorization used below the UI layer.

Navigation visibility is only convenience. Sensitive business operations call
this module as well so a hidden button is never the security boundary.
"""

from __future__ import annotations

import os
import time

from core.db_engine import get_db
from core.logger import get_logger
from core.path_manager import PathManager

logger = get_logger("PharmaKhaatoPermissions")

# Employee IDs are only unique inside one database. Key the cache by both the
# active database identity and employee ID so a demo/test/restored database
# cannot inherit permissions cached for the same numeric ID in another file.
_ROLE_CACHE: dict[tuple[str, int], tuple[str, float]] = {}
_CACHE_TTL = 30.0

_ROLE_PERMISSIONS = {
    "salesman": {
        "pos.sell", "pos.hold", "customer.read", "customer.create",
        "credit.read", "credit.collect", "cash.own_shift",
    },
    "cashier": {
        "pos.sell", "pos.hold", "customer.read", "customer.create",
        "credit.read", "credit.collect", "cash.own_shift",
    },
    "pharmacist": {
        "pos.sell", "pos.hold", "customer.read", "customer.create",
        "credit.read", "credit.collect", "cash.own_shift",
        "inventory.read", "inventory.manage", "reports.read", "returns.process",
    },
    "manager": {"*"},
    "admin": {"*"},
    "administrator": {"*"},
}


def _cache_key(employee_id: int) -> tuple[str, int]:
    """Return a permission-cache key unique to the active SQLite database."""
    try:
        db_path = os.path.realpath(os.path.abspath(PathManager.get_db_path()))
    except Exception:
        # Failing closed is preferable to cross-database permission reuse. An
        # unavailable path gets an isolated sentinel rather than a shared ID.
        db_path = "<unresolved-database>"
    return db_path, int(employee_id)


def clear_permission_cache(employee_id: int | None = None) -> None:
    if employee_id is None:
        _ROLE_CACHE.clear()
        return

    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return

    # Remove this employee from every database context. This also makes role
    # changes immediately effective after administrative account updates.
    for key in [key for key in _ROLE_CACHE if key[1] == employee_id]:
        _ROLE_CACHE.pop(key, None)


def get_employee_role(employee_id: int) -> str | None:
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return None

    key = _cache_key(employee_id)
    cached = _ROLE_CACHE.get(key)
    if cached and time.monotonic() - cached[1] < _CACHE_TTL:
        return cached[0]

    try:
        with get_db() as (_conn, cur):
            cur.execute("SELECT occupation FROM Employee WHERE Employee_id = %s", (employee_id,))
            row = cur.fetchone()
        if not row:
            _ROLE_CACHE.pop(key, None)
            return None
        role = str(row[0] or "").strip().lower()
        _ROLE_CACHE[key] = (role, time.monotonic())
        return role
    except Exception as exc:
        logger.error("Permission role lookup failed: %s", exc)
        return None


def has_permission(employee_id: int, action: str) -> bool:
    role = get_employee_role(employee_id)
    if not role:
        return False
    allowed = _ROLE_PERMISSIONS.get(role, set())
    return "*" in allowed or str(action) in allowed


def require_permission(employee_id: int, action: str) -> tuple[bool, str]:
    if has_permission(employee_id, action):
        return True, ""
    role = get_employee_role(employee_id)
    if role is None:
        return False, "Your staff account could not be verified. Sign in again."
    return False, "Your account does not have permission for this action."
