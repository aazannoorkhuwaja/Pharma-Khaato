from models import CustomerModel, InventoryModel, POSModel
from core.data_revision import touch


class POSController:
    """Coordinates POS workflows across inventory, customer, and transaction models."""

    def __init__(self, pos_model=None, inventory_model=None, customer_model=None):
        self.pos = pos_model or POSModel()
        self.inventory = inventory_model or InventoryModel()
        self.customer = customer_model or CustomerModel()

    @staticmethod
    def _current_employee_id():
        try:
            from ui.app.state.session_state import SessionState
            user = SessionState.get_instance().current_user or {}
            return int(user.get("id")) if user.get("id") is not None else None
        except (TypeError, ValueError):
            return None

    def search_products(self, term): return self.inventory.search_products(term.strip())
    def product_by_barcode(self, barcode): return self.inventory.product_by_barcode(barcode.strip())
    def search_customers(self, text): return self.customer.search(text.strip())
    def customer_total_debt(self, cnic): return self.customer.total_debt(cnic)
    def tax_rate(self): return self.pos.tax_rate()
    def hold_sale(self, customer_id, employee_id, cart): return self.pos.hold_sale(customer_id, employee_id, cart)
    def held_sales(self): return self.pos.held_sales(self._current_employee_id())

    def recall_sale(self, hold_id):
        employee_id = self._current_employee_id()
        if employee_id is None:
            return False, "Sign in again before resuming a held sale."
        return self.pos.recall_sale(hold_id, employee_id)

    def active_session(self, employee_id): return self.pos.active_session(employee_id)
    def checkout_request(self, **kwargs): return self.pos.checkout_request(**kwargs)

    def process_checkout(self, request):
        result = self.pos.process_checkout(request)
        if getattr(result, "success", False):
            # Stock totals changed inside the checkout transaction. Clear the
            # inventory read cache before any other screen can render stale data.
            from core.inventory_service import clear_inventory_cache
            clear_inventory_cache()
            # One committed sale affects several cached read models. Bumping
            # revisions is O(1) and lets navigation refresh only those screens.
            touch("sales", "inventory", "cash", "reports", "credit", "customers")
        return result

    @property
    def discount_threshold_pct(self): return self.pos.discount_threshold_pct
