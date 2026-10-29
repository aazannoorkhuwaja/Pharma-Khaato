"""Backend-facing model facades used by MVC controllers."""

from __future__ import annotations
from typing import Any


class AppModel:
    def initialize_database(self) -> None:
        from core.db_engine import get_conn
        conn = get_conn()
        conn.close()

    def has_registered_employees(self) -> bool:
        from core.auth_service import has_registered_employees
        return has_registered_employees()

    def health(self) -> dict[str, Any]:
        from core.health_service import SystemHealthService
        return SystemHealthService.run_diagnostics()

    def shutdown(self) -> None:
        from core.db_engine import close_all_connections
        close_all_connections()


class AuthModel:
    def login(self, username: str, password: str):
        from core.auth_service import login_user
        return login_user(username, password)

    def register_initial_admin(self, username: str, password: str, first_name: str, last_name: str):
        from core.auth_service import register_initial_admin
        return register_initial_admin(username, password, first_name, last_name)

    def complete_initial_setup(self, username, password, first_name, last_name, settings):
        from core.auth_service import register_initial_admin
        return register_initial_admin(username, password, first_name, last_name, settings=settings)

    def employees(self) -> list:
        from core.auth_service import get_all_employees
        return get_all_employees()

    def create_employee(self, username: str, password: str, first_name: str, last_name: str, occupation: str, actor_id=None):
        from core.auth_service import create_employee
        return create_employee(username, password, first_name, last_name, occupation=occupation, actor_id=actor_id)

    def reset_password(self, employee_id: int, new_password: str, actor_id=None):
        from core.auth_service import update_employee_password
        return update_employee_password(employee_id, new_password, actor_id=actor_id)


class CustomerModel:
    def validate_cnic(self, cnic: str) -> bool:
        from core.customer_service import validate_cnic
        return validate_cnic(cnic)

    def create(self, display_name, phone="", area="", cnic="", employee_id=None):
        from core.customer_service import create_customer
        return create_customer(display_name, phone, area, cnic, employee_id)

    def count(self, text=""):
        from core.customer_directory_service import count_customers
        return count_customers(text)

    def register(self, cnic: str, first_name: str, last_name: str, email: str, city: str):
        from core.customer_service import register_customer
        return register_customer(cnic, first_name, last_name, email, city)

    def search(self, text: str):
        from core.customer_directory_service import search_customers
        return search_customers(text)

    def search_with_debt(self, text: str, limit=120, offset=0):
        from core.customer_directory_service import search_customers_with_debt
        return search_customers_with_debt(text, limit, offset)

    def total_debt(self, cnic: str):
        from core.customer_service import get_customer_total_debt
        return get_customer_total_debt(cnic)

    def debt_aging(self, cnic: str):
        from core.customer_service import get_customer_debt_aging
        return get_customer_debt_aging(cnic)

    def khatoo_summary(self):
        from core.credit_query_service import total_open_credit
        return total_open_credit()


class InventoryModel:
    def supplier_accounts(self):
        from core.supplier_service import supplier_accounts
        return supplier_accounts()

    def supplier_history(self,supplier_id):
        from core.supplier_service import supplier_history
        return supplier_history(supplier_id)

    def supplier_invoice_lines(self,supplier_id):
        from core.supplier_service import invoice_lines
        return invoice_lines(supplier_id)

    def receive_invoice(self,supplier_id,reference,lines,employee_id,operation_id=None,paid_amount=0,payment_method='Bank transfer',terminal_id=None):
        from core.supplier_service import receive_invoice
        return receive_invoice(supplier_id,reference,lines,employee_id,operation_id=operation_id,paid_amount=paid_amount,payment_method=payment_method,terminal_id=terminal_id)

    def pay_supplier(self,supplier_id,amount,employee_id,operation_id=None,payment_method='Bank transfer',note='',terminal_id=None):
        from core.supplier_service import pay_supplier
        return pay_supplier(supplier_id,amount,employee_id,operation_id=operation_id,payment_method=payment_method,note=note,terminal_id=terminal_id)

    def return_to_supplier(self,line_id,quantity,reason,employee_id,operation_id=None):
        from core.supplier_service import return_to_supplier
        return return_to_supplier(line_id,quantity,reason,employee_id,operation_id=operation_id)

    def search_products(self, term: str):
        from core.product_search_service import search_sellable_products
        return search_sellable_products(term)

    def product_by_barcode(self, barcode: str):
        from core.product_search_service import get_product_by_barcode
        return get_product_by_barcode(barcode)

    def products(self):
        from core.inventory_service import get_all_products
        return get_all_products()

    def suppliers(self):
        from core.inventory_service import get_all_suppliers
        return get_all_suppliers()

    @staticmethod
    def _manage(employee_id):
        from core.permission_service import require_permission
        return require_permission(employee_id, "inventory.manage")

    def register_product(self, *args, employee_id=None, operation_id=None, **kwargs):
        allowed, reason = self._manage(employee_id)
        if not allowed:
            return False, reason
        from core.inventory_service import register_product
        return register_product(*args, operation_key=operation_id, **kwargs)

    def register_supplier(self, *args, employee_id=None, operation_id=None, **kwargs):
        allowed, reason = self._manage(employee_id)
        if not allowed:
            return False, reason
        from core.inventory_service import register_supplier
        return register_supplier(*args, operation_key=operation_id, **kwargs)

    def add_batch(self, *args, employee_id=None, operation_id=None, **kwargs):
        allowed, reason = self._manage(employee_id)
        if not allowed:
            return False, reason
        from core.inventory_service import add_batch
        kwargs["operation_key"] = kwargs.get("operation_key") or operation_id
        return add_batch(*args, employee_id=employee_id, **kwargs)

    def near_expiry(self, days: int):
        from core.inventory_service import get_near_expiry
        return get_near_expiry(days)

    def expired_stock(self):
        from core.inventory_service import get_expired_stock
        return get_expired_stock()

    def low_stock(self):
        from core.inventory_service import get_low_stock_products
        return get_low_stock_products()

    def active_batches(self, limit=300):
        from core.inventory_query_service import active_batches
        return active_batches(limit)

    def catalog_snapshot(self, product_limit=400, alert_limit=100):
        from core.inventory_query_service import catalog_snapshot
        return catalog_snapshot(product_limit,alert_limit)

    def catalog_search(self, term, limit=150):
        from core.inventory_query_service import search_catalog_products
        return search_catalog_products(term,limit)

    def sell_units(self, product_id):
        from core.unit_service import get_sell_units
        return get_sell_units(product_id)

    def product_details(self, product_id):
        from core.inventory_service import product_details
        return product_details(product_id)

    def stock_batches(self, product_id=None):
        from core.inventory_service import stock_batches
        return stock_batches(product_id)

    def update_product(self, product_id, *, employee_id=None, operation_id=None, **kwargs):
        allowed, reason = self._manage(employee_id)
        if not allowed:
            return False, reason
        from core.inventory_service import update_product
        return update_product(product_id,employee_id=employee_id,operation_key=operation_id,**kwargs)

    def set_batch_count(self, *args, employee_id=None, operation_id=None, **kwargs):
        allowed, reason = self._manage(employee_id)
        if not allowed:
            return False, reason
        from core.inventory_service import set_batch_count
        kwargs["operation_key"] = kwargs.get("operation_key") or operation_id
        return set_batch_count(*args,employee_id=employee_id,**kwargs)


class POSModel:
    def catalog_matches(self, term):
        from core.inventory_query_service import search_catalog_products
        return bool(search_catalog_products(term, 1))

    def __init__(self):
        self._active_recalled_hold_id: int | None = None

    def hold_sale(self, customer_id, employee_id, cart, *, draft=None):
        from core.hold_sale_service import hold_sale, rehold_sale
        held_sale_id = (draft or {}).get("held_sale_id")
        if held_sale_id is not None:
            ok, result = rehold_sale(
                int(held_sale_id),
                customer_id,
                employee_id,
                cart,
                draft=draft,
            )
            if ok:
                self._active_recalled_hold_id = None
            return ok, result
        return hold_sale(customer_id, employee_id, cart, draft=draft)

    def held_sales(self, employee_id=None):
        from core.hold_sale_service import get_held_sales
        return get_held_sales(employee_id=employee_id)

    def recall_sale(self, hold_id, employee_id):
        from core.hold_sale_service import recall_sale
        ok, result = recall_sale(hold_id, employee_id)
        if ok:
            self._active_recalled_hold_id = int(hold_id)
        return ok, result

    def active_session(self, employee_id: int, terminal_id=None):
        from core.cash_session_service import get_active_session
        return get_active_session(employee_id, terminal_id=terminal_id)

    def tax_rate(self):
        from core.settings_service import SettingsService
        return SettingsService.get_tax_rate()

    def lookup_checkout_result(self, token, employee_id=None):
        from core.checkout_idempotency_service import lookup_checkout_result
        return lookup_checkout_result(token, employee_id)

    def sell_units(self, product_id):
        from core.unit_service import get_sell_units
        return get_sell_units(product_id)

    def receipt_for_sale(self, purchase_id):
        from core.receipt_service import receipt_for_sale
        return receipt_for_sale(purchase_id)

    def reprint_receipt(self, purchase_id):
        from core.receipt_service import reprint_sale_receipt
        return reprint_sale_receipt(purchase_id)

    def checkout_request(self, **kwargs):
        from core.pos_service import CheckoutRequest
        return CheckoutRequest(**kwargs)

    def process_checkout(self, request):
        from core.pos_service import POSTransactionEngine
        # The durable request, rather than mutable model state, identifies the
        # held order that must be completed in the sale transaction.
        result = POSTransactionEngine.process_checkout(request)
        if result.success and self._active_recalled_hold_id is not None:
            self._active_recalled_hold_id = None
        return result

    @property
    def discount_threshold_pct(self) -> float:
        from core.manager_auth_service import DEFAULT_DISCOUNT_THRESHOLD_PCT
        return float(DEFAULT_DISCOUNT_THRESHOLD_PCT)


class ManagerAuthModel:
    def issue_discount_approval(self, username, password, operator_id, discount_amount, subtotal):
        from core.manager_auth_service import issue_discount_approval
        return issue_discount_approval(username, password, operator_id, discount_amount, subtotal)

    def verify(self, username: str, password: str):
        from core.manager_auth_service import verify_manager
        return verify_manager(username, password)

    @property
    def discount_threshold_pct(self) -> float:
        from core.manager_auth_service import DEFAULT_DISCOUNT_THRESHOLD_PCT
        return float(DEFAULT_DISCOUNT_THRESHOLD_PCT)


class KhatooModel:
    @staticmethod
    def _pending_payment_path(employee_id):
        from pathlib import Path
        from core.path_manager import PathManager
        return Path(PathManager.get_config_dir()) / f"pending-credit-payment-{int(employee_id)}.json"

    def load_pending_payment(self, employee_id):
        import json
        path = self._pending_payment_path(employee_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload["employee_id"]) != int(employee_id) or not payload.get("operation_id"):
            raise ValueError("The pending payment recovery record is invalid. Contact the owner.")
        return payload

    def save_pending_payment(self, payload):
        import json, os, tempfile
        path = self._pending_payment_path(payload["employee_id"])
        existing = self.load_pending_payment(payload["employee_id"])
        if existing is not None and existing != payload:
            raise ValueError("Confirm the previous customer payment before starting another.")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".pending-credit-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def clear_pending_payment(self, employee_id, operation_id):
        existing = self.load_pending_payment(employee_id)
        if existing is None:
            return
        if existing["operation_id"] != operation_id:
            raise ValueError("Another payment is awaiting confirmation.")
        self._pending_payment_path(employee_id).unlink()

    def load(self, text="", limit=200, offset=0):
        from core.credit_query_service import load_open_credit
        return load_open_credit(text, limit, offset)

    def accounts(self, text="", limit=100, offset=0):
        from core.credit_query_service import load_credit_accounts
        return load_credit_accounts(text, limit, offset)

    def account_count(self, text=""):
        from core.credit_query_service import count_credit_accounts
        return count_credit_accounts(text)

    def collect(self, customer_ref, amount, employee_id, payment_method="Cash", note="", operation_id=None, terminal_id=None):
        from core.credit_payment_service import record_customer_payment
        return record_customer_payment(customer_ref, amount, employee_id, payment_method, note, operation_id=operation_id, terminal_id=terminal_id)

    def record_payment(self, khatoo_id, amount, employee_id, payment_method="Cash", note="", operation_id=None, terminal_id=None):
        from core.credit_payment_service import record_credit_payment
        return record_credit_payment(khatoo_id, amount, employee_id, payment_method, note, operation_id=operation_id, terminal_id=terminal_id)

    def reverse(self, payment_id, employee_id, reason, operation_id, terminal_id=None):
        from core.credit_payment_service import reverse_credit_payment
        return reverse_credit_payment(payment_id, employee_id, reason, operation_id=operation_id, terminal_id=terminal_id)

    def payment_history(self, limit=100, customer_ref=None, offset=0):
        from core.credit_payment_service import recent_credit_payments
        return recent_credit_payments(limit, customer_ref, offset)

    def payment_count(self, customer_ref=None):
        from core.credit_payment_service import count_credit_payments
        return count_credit_payments(customer_ref)

    def statement(self, customer_ref):
        from core.credit_payment_service import customer_statement_text
        return customer_statement_text(customer_ref)

    def receipt(self, operation_id):
        from core.credit_payment_service import payment_receipt_text
        return payment_receipt_text(operation_id)

    def summary(self):
        from core.credit_query_service import total_open_credit
        return total_open_credit()


class CashSessionModel:
    def last_closed_session(self, employee_id: int | None = None, terminal_id=None):
        from core.cash_query_service import get_last_closed_session
        return get_last_closed_session(employee_id, terminal_id)

    def active_session(self, employee_id: int, terminal_id=None):
        from core.cash_session_service import get_active_session
        return get_active_session(employee_id, terminal_id=terminal_id)

    def open_session(self, employee_id: int, opening_cash: float, terminal_id=None, operation_id=None):
        from core.cash_session_service import open_session
        return open_session(employee_id, opening_cash, terminal_id=terminal_id, operation_id=operation_id)

    def close_session(self, session_id: int, actual_cash: float, notes: str, employee_id=None, terminal_id=None, operation_id=None):
        from core.cash_session_service import close_session
        return close_session(session_id, actual_cash, notes, employee_id=employee_id, terminal_id=terminal_id, operation_id=operation_id)

    def record_movement(self, session_id: int, employee_id: int, movement_type: str, amount: float, reason: str, terminal_id=None, operation_id=None):
        from core.cash_session_service import record_cash_movement
        return record_cash_movement(session_id, employee_id, movement_type, amount, reason, terminal_id=terminal_id, operation_id=operation_id)

    def session_movements(self, session_id, limit=50):
        from core.cash_query_service import get_session_movements
        return get_session_movements(session_id, limit)

    def expected_cash(self, session_id: int):
        from core.cash_session_service import calculate_expected_cash
        return calculate_expected_cash(session_id)

    def cash_summary(self, session_id: int):
        from core.cash_session_service import get_session_cash_summary
        return get_session_cash_summary(session_id)

    def recent_movements(self, limit: int = 50):
        from core.db_engine import get_db
        safe_limit = max(1, min(int(limit), 500))
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT id, session_id, movement_type, amount, reason, created_at "
                f"FROM Cash_Movement ORDER BY id DESC LIMIT {safe_limit}"
            )
            return cur.fetchall()


class ReportsModel:
    def daily_sales(self, selected_date):
        from core.reports_service import get_daily_sales_report
        return get_daily_sales_report(selected_date)

    def credit_collections(self, selected_date):
        from core.reports_service import get_credit_collections_report
        return get_credit_collections_report(selected_date)

    def expiry_alert(self, days: int):
        from core.reports_service import get_expiry_alert_report
        return get_expiry_alert_report(days)

    def reorder_stock(self):
        from core.reports_service import get_reorder_stock_report
        return get_reorder_stock_report()

    def audit_log(self, limit: int):
        from core.reports_service import get_audit_log_report
        return get_audit_log_report(limit)


class SettingsModel:
    def get(self, key: str, default: str | None = None) -> str:
        from core.settings_service import SettingsService
        return SettingsService.get_setting(key, default)

    def get_many(self, keys, defaults=None) -> dict:
        from core.settings_service import SettingsService
        return SettingsService.get_many(keys, defaults)

    def set(self, key: str, value: str, actor_id=None) -> bool:
        from core.settings_service import SettingsService
        return SettingsService.set_setting(key, value, actor_id=actor_id)

    def update(self, values: dict, actor_id=None) -> bool:
        from core.settings_service import SettingsService
        return SettingsService.update_settings(values, actor_id=actor_id)

    def backups(self):
        from core.backup_service import list_backups
        return list_backups()

    def create_backup(self):
        from core.backup_service import create_db_backup
        return create_db_backup()


# Host dispatch uses local classes, never counter-routing factories.
LOCAL_MODELS = {cls.__name__: cls for cls in (AppModel, AuthModel, CustomerModel, InventoryModel, POSModel, ManagerAuthModel, KhatooModel, CashSessionModel, ReportsModel, SettingsModel)}
