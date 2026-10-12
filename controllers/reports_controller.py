from models import ReportsModel


class ReportsController:
    def __init__(self, model: ReportsModel | None = None): self.model = model or ReportsModel()
    def daily_sales(self, selected_date): return self.model.daily_sales(selected_date)
    def expiry_alert(self, days=60): return self.model.expiry_alert(days)
    def reorder_stock(self): return self.model.reorder_stock()
    def audit_log(self, limit=50): return self.model.audit_log(limit)
