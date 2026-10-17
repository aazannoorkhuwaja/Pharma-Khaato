from models import KhatooModel
from core.data_revision import touch


class KhatooController:
    def __init__(self,model=None):
        self.model=model or KhatooModel()

    def load_pending_payment(self, employee_id):
        return self.model.load_pending_payment(employee_id)

    def save_pending_payment(self, payload):
        return self.model.save_pending_payment(payload)

    def clear_pending_payment(self, employee_id, operation_id):
        return self.model.clear_pending_payment(employee_id, operation_id)

    def load(self,text='',limit=200,offset=0):
        return self.model.load(text.strip(),limit,offset)

    def accounts(self,text='',limit=100,offset=0):
        return self.model.accounts(text.strip(),limit,offset)

    def account_count(self,text=''):
        return self.model.account_count(text.strip())

    def collect(self,customer_ref,amount,employee_id,payment_method='Cash',note='',operation_id=None):
        result=self.model.collect(customer_ref,amount,employee_id,payment_method,note,operation_id)
        if result[0]: touch('credit','customers','cash','reports')
        return result

    def record_payment(self,khatoo_id,amount,employee_id,payment_method='Cash',note='',operation_id=None):
        result=self.model.record_payment(khatoo_id,amount,employee_id,payment_method,note,operation_id)
        if result[0]: touch('credit','customers','cash','reports')
        return result

    def reverse(self,payment_id,employee_id,reason,operation_id):
        result=self.model.reverse(payment_id,employee_id,reason,operation_id)
        if result[0]: touch('credit','customers','cash','reports')
        return result

    def payment_history(self,limit=100,customer_ref=None,offset=0):
        return self.model.payment_history(limit,customer_ref,offset)

    def payment_count(self,customer_ref=None): return self.model.payment_count(customer_ref)
    def statement(self,customer_ref): return self.model.statement(customer_ref)
    def receipt(self,operation_id): return self.model.receipt(operation_id)
    def summary(self): return self.model.summary()

    @staticmethod
    def print_text(text):
        from core.receipt_service import print_receipt_spooler
        return print_receipt_spooler(text)
