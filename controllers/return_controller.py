from models.return_model import ReturnModel
from core.data_revision import touch


class ReturnController:
    def __init__(self, model=None):
        self.model = model or ReturnModel()

    def sale(self, purchase_id):
        try:
            purchase_id = int(str(purchase_id).strip().lstrip("#"))
        except (TypeError, ValueError):
            return None
        return self.model.sale(purchase_id)

    def process(self, purchase_id, items, employee_id, reason, condition):
        result = self.model.process(purchase_id, items, employee_id, reason, condition)
        if isinstance(result, tuple) and result and result[0]:
            from core.inventory_service import clear_inventory_cache
            clear_inventory_cache()
            touch("returns", "sales", "inventory", "cash", "credit", "customers", "reports")
        return result
