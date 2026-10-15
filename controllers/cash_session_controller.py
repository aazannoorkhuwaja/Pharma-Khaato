from models import CashSessionModel
from core.data_revision import touch


class CashSessionController:
    def __init__(self, model: CashSessionModel | None = None):
        self.model = model or CashSessionModel()

    def active_session(self, employee_id):
        return self.model.active_session(employee_id)

    def open_session(self, employee_id, opening_cash):
        result = self.model.open_session(employee_id, opening_cash)
        if isinstance(result, tuple) and result and result[0]:
            touch("cash", "reports")
        return result

    def close_session(self, session_id, actual_cash, notes, employee_id):
        result = self.model.close_session(session_id, actual_cash, notes, employee_id)
        if isinstance(result, tuple) and result and result[0]:
            touch("cash", "reports")
        return result

    def record_movement(self, session_id, employee_id, movement_type, amount, reason):
        result = self.model.record_movement(session_id, employee_id, movement_type, amount, reason)
        if isinstance(result, tuple) and result and result[0]:
            touch("cash", "reports")
        return result

    def expected_cash(self, session_id):
        return self.model.expected_cash(session_id)

    def cash_summary(self, session_id):
        return self.model.cash_summary(session_id)

    def recent_movements(self, limit=50):
        return self.model.recent_movements(limit)

    def session_movements(self, session_id, limit=50):
        from core.cash_query_service import get_session_movements
        return get_session_movements(session_id, limit)
