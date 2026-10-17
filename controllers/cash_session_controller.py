from models import CashSessionModel
from core.data_revision import touch


class CashSessionController:
    def __init__(self, model: CashSessionModel | None = None):
        self.model = model or CashSessionModel()

    def active_session(self, employee_id):
        return self.model.active_session(employee_id)

    def open_session(self, employee_id, opening_cash):
        from core.local_operations import perform
        result = perform(employee_id,'open',{'opening_cash':float(opening_cash)},
                         lambda operation: self.model.open_session(employee_id,opening_cash,operation_id=operation))
        if isinstance(result, tuple) and result and result[0]:
            touch("cash", "reports")
        return result

    def close_session(self, session_id, actual_cash, notes):
        from ui.app.state.session_state import SessionState
        employee_id = (SessionState.get_instance().current_user or {}).get('id')
        from core.local_operations import perform
        result = perform(employee_id,'close',{'session_id':session_id,'actual_cash':float(actual_cash),'notes':notes},
                         lambda operation: self.model.close_session(session_id,actual_cash,notes,employee_id=employee_id,operation_id=operation))
        if isinstance(result, tuple) and result and result[0]:
            touch("cash", "reports")
        return result

    def record_movement(self, session_id, employee_id, movement_type, amount, reason):
        from core.local_operations import perform
        result = perform(employee_id,'movement',{'session_id':session_id,'movement_type':movement_type,'amount':float(amount),'reason':reason},
                         lambda operation: self.model.record_movement(session_id,employee_id,movement_type,amount,reason,operation_id=operation))
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
        return self.model.session_movements(session_id, limit)

    def pending_entry(self, employee_id):
        from core.local_operations import pending
        return pending(employee_id)

    def recover_pending(self, employee_id):
        from core.local_operations import pending, perform
        entry = pending(employee_id)
        if entry is None:
            return True, 'There is no pending cash entry.'
        payload=entry['payload']
        def execute(operation):
            if entry['kind']=='open':
                return self.model.open_session(employee_id,**payload,operation_id=operation)
            if entry['kind']=='close':
                return self.model.close_session(employee_id=employee_id,**payload,operation_id=operation)
            if entry['kind']=='movement':
                return self.model.record_movement(employee_id=employee_id,**payload,operation_id=operation)
            raise ValueError('Unknown pending cash entry. Ask the owner for help.')
        result=perform(employee_id,entry['kind'],payload,execute)
        touch('cash','reports')
        return result
