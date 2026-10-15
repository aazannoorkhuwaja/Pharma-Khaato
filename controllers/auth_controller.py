from models import AuthModel


class AuthController:
    def __init__(self, model: AuthModel | None = None):
        self.model = model or AuthModel()

    def login(self, username: str, password: str):
        return self.model.login(username.strip(), password)

    def register_initial_admin(self, username: str, password: str, first_name: str, last_name: str):
        return self.model.register_initial_admin(username.strip(), password, first_name.strip(), last_name.strip())

    def employees(self):
        return self.model.employees()

    def create_employee(self, username, password, first_name, last_name, occupation):
        return self.model.create_employee(username.strip(), password, first_name.strip(), last_name.strip(), occupation)

    def reset_password(self, employee_id: int, new_password: str):
        return self.model.reset_password(employee_id, new_password)
