from models import InventoryModel
from core.data_revision import touch


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

    @staticmethod
    def _after_inventory_mutation(result):
        if isinstance(result, tuple) and result and result[0]:
            touch("inventory", "reports")
        return result

    def search_products(self, term):
        return self.model.search_products(term.strip())

    def product_by_barcode(self, barcode):
        return self.model.product_by_barcode(barcode.strip())

    def products(self):
        return self.model.products()

    def suppliers(self):
        return self.model.suppliers()

    def catalog_snapshot(self, product_limit=400, alert_limit=100):
        from core.inventory_query_service import catalog_snapshot
        return catalog_snapshot(product_limit, alert_limit)

    def catalog_search(self, term, limit=150):
        from core.inventory_query_service import search_catalog_products
        return search_catalog_products(term.strip(), limit)

    def register_product(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        return self._after_inventory_mutation(self.model.register_product(*args, **kwargs))

    def register_supplier(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        return self._after_inventory_mutation(self.model.register_supplier(*args, **kwargs))

    def add_batch(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        return self._after_inventory_mutation(self.model.add_batch(*args, **kwargs))

    def near_expiry(self, days):
        return self.model.near_expiry(days)

    def expired_stock(self):
        return self.model.expired_stock()

    def low_stock(self):
        return self.model.low_stock()

    def active_batches(self, limit=300):
        from core.inventory_query_service import active_batches
        return active_batches(limit)
