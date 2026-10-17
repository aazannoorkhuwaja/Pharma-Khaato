from models import CustomerModel
from core.data_revision import touch


class CustomerController:
    def __init__(self, model: CustomerModel | None = None):
        self.model = model or CustomerModel()

    def validate_cnic(self, cnic): return self.model.validate_cnic(cnic)

    def create(self, display_name, phone="", area="", cnic="", employee_id=None):
        result = self.model.create(display_name, phone, area, cnic, employee_id)
        if result[0]:
            touch("customers")
        return result

    def count(self, text=""): return self.model.count(text)

    def register(self, cnic, first_name, last_name, email, city):
        result = self.model.register(cnic, first_name, last_name, email, city)
        if isinstance(result, tuple) and result and result[0]:
            touch("customers")
        return result

    def search(self, text): return self.model.search(text.strip())
    def search_with_debt(self, text, limit=120, offset=0):
        if limit == 120 and offset == 0:
            return self.model.search_with_debt(text.strip())
        return self.model.search_with_debt(text.strip(), limit, offset)
    def total_debt(self, cnic): return self.model.total_debt(cnic)
    def debt_aging(self, cnic): return self.model.debt_aging(cnic)
    def khatoo_summary(self): return self.model.khatoo_summary()
