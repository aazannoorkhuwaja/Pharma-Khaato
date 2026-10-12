from models import KhatooModel


class KhatooController:
    def __init__(self, model: KhatooModel | None = None): self.model = model or KhatooModel()
    def load(self, text=""): return self.model.load(text.strip())
    def record_payment(self, khatoo_id, amount): return self.model.record_payment(khatoo_id, amount)
    def summary(self): return self.model.summary()
