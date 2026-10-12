from models import InventoryModel


class InventoryController:
    def __init__(self, model: InventoryModel | None = None):
        self.model = model or InventoryModel()

    @staticmethod
    def _mutation_allowed():
        try:
            from ui.app.state.session_state import SessionState
            from core.permission_service import require_permission
            user = SessionState.get_instance().current_user or {}
            employee_id = int(user.get("id"))
            return require_permission(employee_id, "inventory.manage")
        except (TypeError, ValueError):
            return False, "Sign in again before changing stock or products."

    def search_products(self, term): return self.model.search_products(term.strip())
    def product_by_barcode(self, barcode): return self.model.product_by_barcode(barcode.strip())
    def products(self): return self.model.products()
    def suppliers(self): return self.model.suppliers()

    def register_product(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        return self.model.register_product(*args, **kwargs) if allowed else (False, reason)

    def register_supplier(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        return self.model.register_supplier(*args, **kwargs) if allowed else (False, reason)

    def add_batch(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        return self.model.add_batch(*args, **kwargs) if allowed else (False, reason)

    def near_expiry(self, days): return self.model.near_expiry(days)
    def expired_stock(self): return self.model.expired_stock()
    def low_stock(self): return self.model.low_stock()
    def active_batches(self): return self.model.active_batches()
