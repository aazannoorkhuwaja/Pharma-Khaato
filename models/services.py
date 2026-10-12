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
        from core.db_engine import reset_thread_connections
        reset_thread_connections()


class AuthModel:
    def login(self, username: str, password: str):
        from core.auth_service import login_user
        return login_user(username, password)

    def register_initial_admin(self, username: str, password: str, first_name: str, last_name: str):
        from core.auth_service import register_initial_admin
        return register_initial_admin(username, password, first_name, last_name)

    def employees(self) -> list:
        from core.auth_service import get_all_employees
        return get_all_employees()

    def create_employee(self, username: str, password: str, first_name: str, last_name: str, occupation: str):
        from core.auth_service import create_employee
        return create_employee(username, password, first_name, last_name, occupation=occupation)

    def reset_password(self, employee_id: int, new_password: str):
        from core.auth_service import update_employee_password
        return update_employee_password(employee_id, new_password)


class CustomerModel:
    def validate_cnic(self, cnic: str) -> bool:
        from core.customer_service import validate_cnic
        return validate_cnic(cnic)

    def register(self, cnic: str, first_name: str, last_name: str, email: str, city: str):
        from core.customer_service import register_customer
        return register_customer(cnic, first_name, last_name, email, city)

    def search(self, text: str):
        from core.customer_directory_service import search_customers
        return search_customers(text)

    def search_with_debt(self, text: str):
        from core.customer_directory_service import search_customers_with_debt
        return search_customers_with_debt(text)

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

    def register_product(self, *args, **kwargs):
        from core.inventory_service import register_product
        return register_product(*args, **kwargs)

    def register_supplier(self, *args, **kwargs):
        from core.inventory_service import register_supplier
        return register_supplier(*args, **kwargs)

    def add_batch(self, *args, **kwargs):
        from core.inventory_service import add_batch
        return add_batch(*args, **kwargs)

    def near_expiry(self, days: int):
        from core.inventory_service import get_near_expiry
        return get_near_expiry(days)

    def expired_stock(self):
        from core.inventory_service import get_expired_stock
        return get_expired_stock()

    def low_stock(self):
        from core.inventory_service import get_low_stock_products
        return get_low_stock_products()

    def active_batches(self):
        from core.inventory_service import get_all_active_batches
        return get_all_active_batches()


class POSModel:
    def __init__(self):
        self._active_recalled_hold_id: int | None = None

    def hold_sale(self, customer_id, employee_id, cart):
        from core.hold_sale_service import hold_sale, rehold_sale
        if self._active_recalled_hold_id is not None:
            ok, result = rehold_sale(
                self._active_recalled_hold_id,
                customer_id,
                employee_id,
                cart,
            )
            if ok:
                self._active_recalled_hold_id = None
            return ok, result
        return hold_sale(customer_id, employee_id, cart)

    def held_sales(self, employee_id=None):
        from core.hold_sale_service import get_held_sales
        return get_held_sales(employee_id=employee_id)

    def recall_sale(self, hold_id, employee_id):
        from core.hold_sale_service import recall_sale
        ok, result = recall_sale(hold_id, employee_id)
        if ok:
            self._active_recalled_hold_id = int(hold_id)
        return ok, result

    def active_session(self, employee_id: int):
        from core.cash_session_service import get_active_session
        return get_active_session(employee_id)

    def tax_rate(self):
        from core.settings_service import SettingsService
        return SettingsService.get_tax_rate()

    def checkout_request(self, **kwargs):
        from core.pos_service import CheckoutRequest
        return CheckoutRequest(**kwargs)

    def process_checkout(self, request):
        from core.pos_service import POSTransactionEngine
        result = POSTransactionEngine.process_checkout(request)
        if result.success and self._active_recalled_hold_id is not None:
            try:
                from core.hold_sale_service import complete_hold
                complete_hold(
                    self._active_recalled_hold_id,
                    request.employee_id,
                    result.purchase_id,
                )
            finally:
                self._active_recalled_hold_id = None
        return result

    @property
    def discount_threshold_pct(self) -> float:
        from core.manager_auth_service import DEFAULT_DISCOUNT_THRESHOLD_PCT
        return float(DEFAULT_DISCOUNT_THRESHOLD_PCT)


class ManagerAuthModel:
    def verify(self, username: str, password: str):
        from core.manager_auth_service import verify_manager
        return verify_manager(username, password)

    @property
    def discount_threshold_pct(self) -> float:
        from core.manager_auth_service import DEFAULT_DISCOUNT_THRESHOLD_PCT
        return float(DEFAULT_DISCOUNT_THRESHOLD_PCT)


class KhatooModel:
    def load(self, text: str):
        from core.credit_query_service import load_open_credit
        return load_open_credit(text)

    def record_payment(self, khatoo_id: int, amount: float, employee_id: int, payment_method: str = "Cash", note: str = ""):
        from core.credit_payment_service import record_credit_payment
        return record_credit_payment(khatoo_id, amount, employee_id, payment_method, note)

    def payment_history(self, limit: int = 100):
        from core.credit_payment_service import recent_credit_payments
        return recent_credit_payments(limit)

    def summary(self):
        from core.credit_query_service import total_open_credit
        return total_open_credit()


class CashSessionModel:
    def active_session(self, employee_id: int):
        from core.cash_session_service import get_active_session
        return get_active_session(employee_id)

    def open_session(self, employee_id: int, opening_cash: float):
        from core.cash_session_service import open_session
        return open_session(employee_id, opening_cash)

    def close_session(self, session_id: int, actual_cash: float, notes: str):
        from core.cash_session_service import close_session
        return close_session(session_id, actual_cash, notes)

    def record_movement(self, session_id: int, employee_id: int, movement_type: str, amount: float, reason: str):
        from core.cash_session_service import record_cash_movement
        return record_cash_movement(session_id, employee_id, movement_type, amount, reason)

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

    def set(self, key: str, value: str) -> bool:
        from core.settings_service import SettingsService
        return SettingsService.set_setting(key, value)

    def update(self, values: dict) -> bool:
        from core.settings_service import SettingsService
        return SettingsService.update_settings(values)

    def backups(self):
        from core.backup_service import list_backups
        return list_backups()

    def create_backup(self):
        from core.backup_service import create_db_backup
        return create_db_backup()
