"""Central role/action authorization used below the UI layer.

Navigation visibility is only convenience. Sensitive business operations call
this module as well so a hidden button is never the security boundary.
"""

from __future__ import annotations

import time
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoPermissions")

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


def clear_permission_cache(employee_id: int | None = None) -> None:
    if employee_id is None:
        _ROLE_CACHE.clear()
    else:
        for key in list(_ROLE_CACHE):
            if key[1] == int(employee_id):
                _ROLE_CACHE.pop(key, None)


def get_employee_role(employee_id: int) -> str | None:
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return None

    from core.path_manager import PathManager
    cache_key = (PathManager.get_db_path(), employee_id)
    cached = _ROLE_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[1] < _CACHE_TTL:
        return cached[0]

    try:
        with get_db() as (_conn, cur):
            cur.execute("SELECT occupation FROM Employee WHERE Employee_id = %s", (employee_id,))
            row = cur.fetchone()
        if not row:
            return None
        role = str(row[0] or "").strip().lower()
        _ROLE_CACHE[cache_key] = (role, time.monotonic())
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
