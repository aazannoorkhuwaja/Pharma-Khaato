from models import AuthModel, SettingsModel
from core.data_revision import touch


class SettingsController:
    def __init__(self, settings_model=None, auth_model=None):
        self.settings = settings_model or SettingsModel()
        self.auth = auth_model or AuthModel()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def get_many(self, keys, defaults=None):
        return self.settings.get_many(keys, defaults)

    def set(self, key, value):
        result = self.settings.set(key, value)
        if result:
            touch("settings")
        return result

    def update(self, values):
        result = self.settings.update(values)
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
    def create_support_bundle():
        from core.support_service import create_support_bundle
        return create_support_bundle()

    def employees(self):
        return self.auth.employees()

    def create_employee(self, username, password, first_name, last_name, occupation):
        result = self.auth.create_employee(username, password, first_name, last_name, occupation)
        if isinstance(result, tuple) and result and result[0]:
            touch("staff")
        return result

    def reset_password(self, employee_id, new_password):
        result = self.auth.reset_password(employee_id, new_password)
        if isinstance(result, tuple) and result and result[0]:
            touch("staff")
        return result

    @staticmethod
    def receipt_template_options():
        from core.receipt_service import get_receipt_template_options
        return get_receipt_template_options()

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
