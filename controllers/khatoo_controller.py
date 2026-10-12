from models import KhatooModel


class KhatooController:
    def __init__(self, model: KhatooModel | None = None):
        self.model = model or KhatooModel()

    def load(self, text=""):
        return self.model.load(text.strip())

    def record_payment(self, khatoo_id, amount, employee_id, payment_method="Cash", note=""):
        return self.model.record_payment(khatoo_id, amount, employee_id, payment_method, note)

    def payment_history(self, limit=100):
        return self.model.payment_history(limit)

    def summary(self):
        return self.model.summary()
