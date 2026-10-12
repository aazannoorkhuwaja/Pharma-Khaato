"""User-facing terminology for Pharma-Khaato.

This module deliberately separates UI language from backend/domain values.
That keeps the interface easy to rename/localise without changing business
logic (for example a friendly "Customer Credit" label can still map to the
canonical backend value ``Khatoo Credit``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    compact_label: str
    shortcut: str
    help_text: str


NAV_ITEMS = (
    NavItem("pos", "New Sale", "Sale", "Alt+1", "Start a sale and take payment."),
    NavItem("customers", "Customers", "Cust.", "Alt+2", "Find customers and view what they owe."),
    NavItem("khatoo", "Customer Credit", "Credit", "Alt+3", "View customer credit and record payments."),
    NavItem("inventory", "Stock & Products", "Stock", "Alt+4", "Manage products, batches, stock, and expiry alerts."),
    NavItem("cash_session", "Shift & Cash", "Shift", "Alt+5", "Open or close the cash shift and record drawer cash."),
    NavItem("reports", "Reports", "Report", "Alt+6", "Review sales, low stock, expiry, and activity."),
    NavItem("settings", "Settings", "Setup", "Alt+7", "Change pharmacy settings, staff access, and backups."),
)

NAV_BY_KEY = {item.key: item for item in NAV_ITEMS}

# Display label -> stable backend value.  Never make business logic depend on
# translated or revised UI wording.
PAYMENT_OPTIONS = (
    ("Cash", "Cash"),
    ("Card", "Credit Card"),
    ("Easypaisa", "Easypaisa"),
    ("JazzCash", "JazzCash"),
    ("Customer Credit", "Khatoo Credit"),
)

CASH_MOVEMENT_OPTIONS = (
    ("Cash In", "CASH_IN"),
    ("Cash Out", "CASH_OUT"),
    ("Refund", "REFUND"),
)

CASH_MOVEMENT_LABELS = {value: label for label, value in CASH_MOVEMENT_OPTIONS}

ROLE_OPTIONS = (
    ("Cashier", "Salesman"),
    ("Pharmacist", "Pharmacist"),
    ("Administrator", "Admin"),
)

ROLE_LABELS = {value.lower(): label for label, value in ROLE_OPTIONS}


def role_label(value: str) -> str:
    """Return a friendly role name while keeping unknown custom roles intact."""
    raw = str(value or "Staff")
    return ROLE_LABELS.get(raw.lower(), raw)
