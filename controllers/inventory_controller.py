from models import InventoryModel


class InventoryController:
    def __init__(self, model: InventoryModel | None = None):
        self.model = model or InventoryModel()

    def search_products(self, term): return self.model.search_products(term.strip())
    def product_by_barcode(self, barcode): return self.model.product_by_barcode(barcode.strip())
    def products(self): return self.model.products()
    def suppliers(self): return self.model.suppliers()
    def register_product(self, *args, **kwargs): return self.model.register_product(*args, **kwargs)
    def register_supplier(self, *args, **kwargs): return self.model.register_supplier(*args, **kwargs)
    def add_batch(self, *args, **kwargs): return self.model.add_batch(*args, **kwargs)
    def near_expiry(self, days): return self.model.near_expiry(days)
    def expired_stock(self): return self.model.expired_stock()
    def low_stock(self): return self.model.low_stock()
    def active_batches(self): return self.model.active_batches()
