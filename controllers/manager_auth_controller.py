from models import ManagerAuthModel


class ManagerAuthController:
    def __init__(self, model: ManagerAuthModel | None = None):
        self.model = model or ManagerAuthModel()

    def verify(self, username: str, password: str):
        return self.model.verify(username.strip(), password)

    def issue_discount_approval(self, username, password, operator_id, discount_amount, subtotal):
        return self.model.issue_discount_approval(username.strip(), password, operator_id, discount_amount, subtotal)

    @property
    def discount_threshold_pct(self) -> float:
        return self.model.discount_threshold_pct
