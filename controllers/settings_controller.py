from models import AuthModel, SettingsModel


class SettingsController:
    def __init__(self, settings_model=None, auth_model=None):
        self.settings = settings_model or SettingsModel()
        self.auth = auth_model or AuthModel()

    def get(self, key, default=None): return self.settings.get(key, default)
    def set(self, key, value): return self.settings.set(key, value)
    def update(self, values): return self.settings.update(values)
    def backups(self): return self.settings.backups()
    def create_backup(self): return self.settings.create_backup()
    def employees(self): return self.auth.employees()
    def create_employee(self, username, password, first_name, last_name, occupation): return self.auth.create_employee(username, password, first_name, last_name, occupation)
    def reset_password(self, employee_id, new_password): return self.auth.reset_password(employee_id, new_password)
