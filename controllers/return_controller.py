from models.return_model import ReturnModel


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
        return self.model.process(purchase_id, items, employee_id, reason, condition)
