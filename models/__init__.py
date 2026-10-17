"""MVC model layer for Pharma-Khaato.

The model layer exposes business/data operations to controllers while keeping Qt
out of the backend. Existing ``core`` services remain the implementation layer;
views should not import them directly.
"""

from .services import (
    AppModel,
    AuthModel,
    CashSessionModel,
    CustomerModel,
    InventoryModel,
    ManagerAuthModel,
    KhatooModel,
    POSModel,
    ReportsModel,
    SettingsModel,
)

from .remote import routed_model

for _name in (
    'AppModel', 'AuthModel', 'CashSessionModel', 'CustomerModel', 'InventoryModel',
    'ManagerAuthModel', 'KhatooModel', 'POSModel', 'ReportsModel', 'SettingsModel',
):
    globals()[_name] = routed_model(globals()[_name])

__all__ = [
    "AppModel",
    "AuthModel",
    "CashSessionModel",
    "CustomerModel",
    "InventoryModel",
    "ManagerAuthModel",
    "KhatooModel",
    "POSModel",
    "ReportsModel",
    "SettingsModel",
]
