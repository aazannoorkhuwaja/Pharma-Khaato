from models import AuthModel, SettingsModel
from core.data_revision import touch


class SettingsController:
    def __init__(self, settings_model=None, auth_model=None):
        self.settings = settings_model or SettingsModel()
        self.auth = auth_model or AuthModel()

    @staticmethod
    def _actor_id():
        from ui.app.state.session_state import SessionState
        user = SessionState.get_instance().current_user or {}
        return user.get("id") or user.get("emp_id")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def get_many(self, keys, defaults=None):
        return self.settings.get_many(keys, defaults)

    def set(self, key, value):
        result = self.settings.set(key, value, actor_id=self._actor_id())
        if result:
            touch("settings")
        return result

    def update(self, values):
        result = self.settings.update(values, actor_id=self._actor_id())
        if result:
            touch("settings")
        return result

    def backups(self):
        return self.settings.backups()

    def create_backup(self):
        result = self.settings.create_backup()
        if isinstance(result, tuple) and result and result[0]:
            touch("backups")
        return result

    @staticmethod
    def restore_backup(filepath: str, employee_id: int):
        from core.lan_config import load_counter_config
        if load_counter_config():
            return False, "Restore backups on the main shop computer, then restart all counters."
        from core.backup_service import restore_database
        from core.permission_service import require_permission

        allowed, message = require_permission(employee_id, "settings.restore")
        if not allowed:
            return False, message
        result = restore_database(filepath, require_restart=True)
        if isinstance(result, tuple) and result and result[0]:
            for domain in ("settings", "staff", "inventory", "customers", "credit", "cash", "sales", "returns", "reports", "backups"):
                touch(domain)
        return result

    @staticmethod
    def create_support_bundle():
        from core.support_service import create_support_bundle
        return create_support_bundle()

    def employees(self):
        return self.auth.employees()

    def create_employee(self, username, password, first_name, last_name, occupation):
        result = self.auth.create_employee(username, password, first_name, last_name, occupation, actor_id=self._actor_id())
        if isinstance(result, tuple) and result and result[0]:
            touch("staff")
        return result

    def reset_password(self, employee_id, new_password):
        result = self.auth.reset_password(employee_id, new_password, actor_id=self._actor_id())
        if isinstance(result, tuple) and result and result[0]:
            touch("staff")
        return result

    @staticmethod
    def backup_destination():
        from core.lan_config import load_counter_config
        if load_counter_config():
            return "Managed on the main shop computer"
        from core.backup_service import backup_destination
        return backup_destination()

    def configure_backup_destination(self, destination):
        from core.permission_service import require_permission
        from core.lan_config import load_counter_config
        if load_counter_config():
            return False, "Choose the backup location on the main shop computer."
        from core.backup_service import configure_backup_destination
        allowed, message = require_permission(self._actor_id(), "settings.manage")
        if not allowed:
            return False, message
        try:
            return configure_backup_destination(destination)
        except OSError:
            return False, "This backup location is unavailable or is not writable."

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
