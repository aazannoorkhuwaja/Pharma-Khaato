from models import AuthModel, SettingsModel
from core.data_revision import touch


class SettingsController:
    def __init__(self, settings_model=None, auth_model=None):
        self.settings = settings_model or SettingsModel()
        self.auth = auth_model or AuthModel()

    def get(self, key, default=None):
        return self.settings.get(key, default)

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
