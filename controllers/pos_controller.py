import uuid
import copy

from models import CustomerModel, InventoryModel, POSModel
from core.data_revision import current, touch


class POSController:
    """Coordinates POS workflows across inventory, customer, and transaction models."""

    def __init__(self, pos_model=None, inventory_model=None, customer_model=None):
        self.pos = pos_model or POSModel()
        self.inventory = inventory_model or InventoryModel()
        self.customer = customer_model or CustomerModel()
        self._tax_rate_cache = None
        self._tax_settings_revision = None

    @staticmethod
    def _current_employee_id():
        try:
            from ui.app.state.session_state import SessionState
            user = SessionState.get_instance().current_user or {}
            return int(user.get("id")) if user.get("id") is not None else None
        except (TypeError, ValueError):
            return None

    def search_products(self, term):
        return self.inventory.search_products(term.strip())

    def product_by_barcode(self, barcode):
        return self.inventory.product_by_barcode(barcode.strip())

    def search_customers(self, text):
        return self.customer.search(text.strip())

    def customer_total_debt(self, cnic):
        return self.customer.total_debt(cnic)

    def tax_rate(self):
        """Return tax without re-reading Settings on every cart repaint."""
        revision = current("settings")
        if self._tax_rate_cache is None or self._tax_settings_revision != revision:
            self._tax_rate_cache = self.pos.tax_rate()
            self._tax_settings_revision = revision
        return self._tax_rate_cache

    def hold_sale(self, customer_id, employee_id, cart, draft=None):
        return self.pos.hold_sale(customer_id, employee_id, cart, draft=draft)

    def sell_units(self, product_id):
        return self.pos.sell_units(product_id)

    def reprint_receipt(self, purchase_id):
        return self.pos.reprint_receipt(purchase_id)

    def receipt_for_sale(self, purchase_id):
        return self.pos.receipt_for_sale(purchase_id)

    def lookup_checkout_result(self, token, employee_id):
        return self.pos.lookup_checkout_result(token, employee_id=employee_id)

    @staticmethod
    def pending_checkout_path(employee_id):
        from core.path_manager import PathManager
        from pathlib import Path
        return Path(PathManager.get_config_dir()) / f"pending-checkout-{int(employee_id)}.json"

    def held_sales(self, employee_id=None):
        return self.pos.held_sales(employee_id if employee_id is not None else self._current_employee_id())

    def recall_sale(self, hold_id, employee_id=None):
        employee_id = employee_id if employee_id is not None else self._current_employee_id()
        if employee_id is None:
            return False, "Sign in again before resuming a held sale."
        return self.pos.recall_sale(hold_id, employee_id)

    def active_session(self, employee_id):
        return self.pos.active_session(employee_id)

    def checkout_request(self, **kwargs):
        """Build a request with a stable token reused across checkout retries."""
        from ui.app.state.session_state import SessionState

        session = SessionState.get_instance()
        token = kwargs.pop("checkout_token", None) or session.checkout_token or uuid.uuid4().hex
        request = self.pos.checkout_request(**copy.deepcopy(kwargs), checkout_token=token)
        session.checkout_token = token
        return request

    def process_checkout(self, request):
        from core.checkout_idempotency_service import process_checkout_idempotently

        result = process_checkout_idempotently(request, self.pos.process_checkout)
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
    def discount_threshold_pct(self):
        return self.pos.discount_threshold_pct
