"""Qt-free facade for the Returns & Refunds workflow."""


class ReturnModel:
    def sale(self, purchase_id: int):
        from core.return_service import get_returnable_sale
        return get_returnable_sale(purchase_id)

    def process(self, purchase_id: int, items: list, employee_id: int, reason: str, condition: str):
        from core.return_service import process_return
        return process_return(
            purchase_id,
            items,
            employee_id,
            reason=reason,
            condition=condition,
        )
