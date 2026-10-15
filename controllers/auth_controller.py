from models import AuthModel


class AuthController:
    def __init__(self, model: AuthModel | None = None):
        self.model = model or AuthModel()

    @staticmethod
    def _current_employee_id():
        try:
            from ui.app.state.session_state import SessionState
            user = SessionState.get_instance().current_user or {}
            return int(user.get("id") or user.get("emp_id") or 0) or None
        except (TypeError, ValueError, AttributeError):
            return None

    @classmethod
    def _authorize_staff_management(cls, employee_id=None):
        if employee_id is None:
            employee_id = cls._current_employee_id()
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return False, "Sign in again before managing staff accounts."
        from core.permission_service import require_permission
        return require_permission(employee_id, "staff.manage")

    def login(self, username: str, password: str):
        return self.model.login(username.strip(), password)

    def register_initial_admin(self, username: str, password: str, first_name: str, last_name: str):
        # Initial-admin creation remains bootstrap-safe in auth_service, which
        # is responsible for ensuring this path is only used for first setup.
        return self.model.register_initial_admin(username.strip(), password, first_name.strip(), last_name.strip())

    def employees(self, employee_id=None):
        allowed, _reason = self._authorize_staff_management(employee_id)
        if not allowed:
            return []
        return self.model.employees()

    def create_employee(self, username, password, first_name, last_name, occupation, employee_id=None):
        allowed, reason = self._authorize_staff_management(employee_id)
        if not allowed:
            return False, reason
        return self.model.create_employee(username.strip(), password, first_name.strip(), last_name.strip(), occupation)

    def reset_password(self, target_employee_id: int, new_password: str, employee_id=None):
        allowed, reason = self._authorize_staff_management(employee_id)
        if not allowed:
            return False, reason
        return self.model.reset_password(target_employee_id, new_password)
