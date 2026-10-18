"""Qt-free facade for the Returns & Refunds workflow."""


class ReturnModel:
    def sale(self, purchase_id: int):
        from core.return_service import get_returnable_sale
        return get_returnable_sale(purchase_id)

    def operation_status(self, operation_id, employee_id):
        from core.return_service import lookup_return_result
        return lookup_return_result(operation_id, employee_id)

    def process(self, purchase_id: int, items: list, employee_id: int, reason: str, condition: str, operation_id=None):
        from core.return_service import process_return
        return process_return(
            purchase_id,
            items,
            employee_id,
            reason=reason,
            condition=condition,
            operation_id=operation_id,
        )


LOCAL_RETURN_MODEL = ReturnModel
from models.remote import routed_model
ReturnModel = routed_model(LOCAL_RETURN_MODEL)
