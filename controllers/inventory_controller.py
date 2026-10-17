from models import InventoryModel
from core.data_revision import touch


class InventoryController:
    def __init__(self, model: InventoryModel | None = None):
        self.model = model or InventoryModel()

    @staticmethod
    def _mutation_allowed():
        try:
            from ui.app.state.session_state import SessionState
            user = SessionState.get_instance().current_user or {}
            employee_id = int(user.get("id"))
            return True, ""
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
        return self.model.catalog_snapshot(product_limit, alert_limit)

    def catalog_search(self, term, limit=150):
        return self.model.catalog_search(term.strip(), limit)

    @staticmethod
    def _employee_id():
        from ui.app.state.session_state import SessionState
        return int((SessionState.get_instance().current_user or {})["id"])

    def sell_units(self, product_id):
        return self.model.sell_units(product_id)

    def product_details(self, product_id):
        return self.model.product_details(product_id)

    def update_product(self, product_id, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        kwargs["employee_id"] = self._employee_id()
        return self._after_inventory_mutation(self.model.update_product(product_id, **kwargs))

    def stock_batches(self, product_id=None):
        return self.model.stock_batches(product_id)

    def set_batch_count(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        kwargs["employee_id"] = self._employee_id()
        return self._after_inventory_mutation(self.model.set_batch_count(*args, **kwargs))

    def register_product(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        kwargs["employee_id"] = self._employee_id()
        return self._after_inventory_mutation(self.model.register_product(*args, **kwargs))

    def register_supplier(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        kwargs["employee_id"] = self._employee_id()
        return self._after_inventory_mutation(self.model.register_supplier(*args, **kwargs))

    def add_batch(self, *args, **kwargs):
        allowed, reason = self._mutation_allowed()
        if not allowed:
            return False, reason
        employee=self._employee_id()
        kwargs["employee_id"] = employee
        kwargs.pop('operation_key',None)
        kwargs.pop('operation_id',None)
        from core.local_operations import perform
        payload={'args':list(args),'kwargs':kwargs}
        return self._after_inventory_mutation(perform(employee,'receiving',payload,
            lambda operation:self.model.add_batch(*args,**kwargs,operation_id=operation),domain='stock'))

    def recover_stock_entry(self):
        from core.local_operations import pending,perform
        employee=self._employee_id()
        entry=pending(employee,domain='stock')
        if entry is None:
            return True,'There is no pending stock entry.'
        payload=entry['payload']
        return self._after_inventory_mutation(perform(employee,entry['kind'],payload,
            lambda operation:self.model.add_batch(*payload['args'],**payload['kwargs'],operation_id=operation),domain='stock'))

    def supplier_accounts(self):
        return self.model.supplier_accounts()

    def supplier_history(self,supplier_id):
        return self.model.supplier_history(supplier_id)

    def supplier_invoice_lines(self,supplier_id):
        return self.model.supplier_invoice_lines(supplier_id)

    def _supplier_write(self,kind,payload):
        from core.local_operations import perform
        employee=self._employee_id()
        def execute(operation):
            return getattr(self.model,kind)(**payload,employee_id=employee,operation_id=operation)
        return self._after_inventory_mutation(perform(employee,kind,payload,execute,domain='supplier'))

    def receive_invoice(self,**payload):
        return self._supplier_write('receive_invoice',payload)

    def pay_supplier(self,**payload):
        return self._supplier_write('pay_supplier',payload)

    def return_to_supplier(self,**payload):
        return self._supplier_write('return_to_supplier',payload)

    def recover_supplier_entry(self):
        from core.local_operations import pending
        entry=pending(self._employee_id(),domain='supplier')
        if entry is None:
            return True,'There is no pending supplier entry.',None
        return self._supplier_write(entry['kind'],entry['payload'])

    def near_expiry(self, days):
        return self.model.near_expiry(days)

    def expired_stock(self):
        return self.model.expired_stock()

    def low_stock(self):
        return self.model.low_stock()

    def active_batches(self, limit=300):
        return self.model.active_batches(limit)


def business_date():
    from core.business_time import business_date as shop_date
    return shop_date()
