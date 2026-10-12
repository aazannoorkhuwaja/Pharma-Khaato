from models import CashSessionModel


class CashSessionController:
    def __init__(self, model: CashSessionModel | None = None):
        self.model = model or CashSessionModel()

    def active_session(self, employee_id):
        return self.model.active_session(employee_id)

    def open_session(self, employee_id, opening_cash):
        return self.model.open_session(employee_id, opening_cash)

    def close_session(self, session_id, actual_cash, notes):
        return self.model.close_session(session_id, actual_cash, notes)

    def record_movement(self, session_id, employee_id, movement_type, amount, reason):
        return self.model.record_movement(session_id, employee_id, movement_type, amount, reason)

    def expected_cash(self, session_id):
        return self.model.expected_cash(session_id)

    def cash_summary(self, session_id):
        return self.model.cash_summary(session_id)

    def recent_movements(self, limit=50):
        return self.model.recent_movements(limit)
