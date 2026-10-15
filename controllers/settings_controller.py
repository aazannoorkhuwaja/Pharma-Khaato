from models import AuthModel, SettingsModel
from core.data_revision import touch


class SettingsController:
    """MVC boundary for pharmacy settings and administrative operations.

    Read-only presentation preferences remain broadly readable. Business-rule,
    staff-account, backup, support and restore mutations validate the acting
    employee here so hiding a Settings tab is never the authorization boundary.
    Initial setup is the only unauthenticated exception and is allowed only
    while no employee account exists yet.
    """

    _SENSITIVE_SETTING_KEYS = {
        "default_tax_rate",
        "max_customer_credit_limit",
        "near_expiry_days",
        "expiry_warning_threshold_days",
        "pharmacy_name",
        "slogan",
        "address",
        "phone",
        "license_number",
        "ntn_number",
        "receipt_header_text",
        "receipt_footer",
        "receipt_footer_text",
        "receipt_template",
        "preferred_printer",
        "receipt_auto_print",
    }

    def __init__(self, settings_model=None, auth_model=None):
        self.settings = settings_model or SettingsModel()
        self.auth = auth_model or AuthModel()

    @staticmethod
    def _has_registered_employees() -> bool:
        try:
            from core.auth_service import has_registered_employees
            return bool(has_registered_employees())
        except Exception:
            # Fail closed once account state cannot be established.
            return True

    @staticmethod
    def _current_employee_id():
        try:
            from ui.app.state.session_state import SessionState
            user = SessionState.get_instance().current_user or {}
            return int(user.get("id") or user.get("emp_id") or 0) or None
        except (TypeError, ValueError, AttributeError):
            return None

    @classmethod
    def _authorize(cls, employee_id, action, *, allow_before_setup=False):
        if allow_before_setup and not cls._has_registered_employees():
            return True, ""
        if employee_id is None:
            employee_id = cls._current_employee_id()
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return False, "Sign in again before changing administrative settings."
        from core.permission_service import require_permission
        return require_permission(employee_id, action)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def get_many(self, keys, defaults=None):
        return self.settings.get_many(keys, defaults)

    def set(self, key, value, employee_id=None):
        if str(key) in self._SENSITIVE_SETTING_KEYS:
            allowed, _reason = self._authorize(
                employee_id, "settings.manage", allow_before_setup=True
            )
            if not allowed:
                return False
        result = self.settings.set(key, value)
        if result:
            touch("settings")
        return result

    def update(self, values, employee_id=None):
        keys = {str(key) for key in dict(values or {})}
        if keys & self._SENSITIVE_SETTING_KEYS:
            allowed, _reason = self._authorize(
                employee_id, "settings.manage", allow_before_setup=True
            )
            if not allowed:
                return False
        result = self.settings.update(values)
        if result:
            touch("settings")
        return result

    def backups(self):
        return self.settings.backups()

    def create_backup(self, employee_id=None):
        allowed, reason = self._authorize(employee_id, "settings.manage")
        if not allowed:
            return False, reason
        result = self.settings.create_backup()
        if isinstance(result, tuple) and result and result[0]:
            touch("backups")
        return result

    @staticmethod
    def restore_backup(filepath: str, employee_id: int):
        from core.backup_service import restore_database
        from core.permission_service import require_permission

        allowed, message = require_permission(employee_id, "settings.restore")
        if not allowed:
            return False, message
        result = restore_database(filepath)
        if isinstance(result, tuple) and result and result[0]:
            for domain in ("settings", "staff", "inventory", "customers", "credit", "cash", "sales", "returns", "reports", "backups"):
                touch(domain)
        return result

    @classmethod
    def create_support_bundle(cls, employee_id=None):
        allowed, reason = cls._authorize(employee_id, "settings.manage")
        if not allowed:
            return False, reason
        from core.support_service import create_support_bundle
        return create_support_bundle()

    def employees(self):
        return self.auth.employees()

    def create_employee(self, username, password, first_name, last_name, occupation, employee_id=None):
        allowed, reason = self._authorize(employee_id, "staff.manage")
        if not allowed:
            return False, reason
        result = self.auth.create_employee(username, password, first_name, last_name, occupation)
        if isinstance(result, tuple) and result and result[0]:
            touch("staff")
        return result

    def reset_password(self, target_employee_id, new_password, employee_id=None):
        allowed, reason = self._authorize(employee_id, "staff.manage")
        if not allowed:
            return False, reason
        result = self.auth.reset_password(target_employee_id, new_password)
        if isinstance(result, tuple) and result and result[0]:
            touch("staff")
        return result

    @staticmethod
    def receipt_template_options():
        from core.receipt_service import get_receipt_template_options
        return get_receipt_template_options()

    @staticmethod
    def available_printers():
        from core.receipt_service import available_printers
        return available_printers()

    @staticmethod
    def print_test_receipt(printer_name=None, template=None):
        from core.receipt_service import print_test_receipt
        return print_test_receipt(printer_name, template)

    @staticmethod
    def receipt_preview(template):
        from core.receipt_service import generate_invoice_text
        return generate_invoice_text(
            1024,
            "Walk-in Customer",
            [
                {"name": "Augmentin 625mg", "qty": 1, "price": 450.0},
                {"name": "Panadol 500mg", "qty": 2, "price": 50.0},
                {"name": "Brufen 400mg", "qty": 1, "price": 80.0},
            ],
            total=630.0,
            tax=0.0,
            discount=0.0,
            payment_method="Cash",
            cashier_name="Admin",
            amount_received=1000.0,
            change=370.0,
            template=template,
        )
