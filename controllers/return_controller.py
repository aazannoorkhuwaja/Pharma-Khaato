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

    def operation_status(self, operation_id, employee_id):
        return self.model.operation_status(operation_id, employee_id)

    def pending_path(self, employee_id):
        from pathlib import Path
        from core.path_manager import PathManager
        return Path(PathManager.get_config_dir()) / f"pending_return_{int(employee_id)}.json"

    def process(self, purchase_id, items, employee_id, reason, condition, operation_id=None):
        result = self.model.process(purchase_id, items, employee_id, reason, condition, operation_id=operation_id)
        if isinstance(result, tuple) and result and result[0]:
            from core.inventory_service import clear_inventory_cache
            clear_inventory_cache()
            touch("returns", "sales", "inventory", "cash", "credit", "customers", "reports")
        return result
