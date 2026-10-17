"""Business-level regression checks for transaction identity and recorded facts."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
import threading

import pytest


def request(employee_id, token="financial-test", **changes):
    from core.pos_service import CheckoutRequest
    values = dict(customer_id="WALKIN", employee_id=employee_id,
                  cart=[{"prod_id": 1, "batch_id": 1, "qty": 1, "price": 15}],
                  payment_method="Easypaisa", checkout_token=token)
    values.update(changes)
    return CheckoutRequest(**values)


def query(shop, sql, params=()):
    cur = shop.get_conn().cursor()
    cur.execute(sql, params)
    return cur.fetchone()


@pytest.mark.parametrize("percentage,rate", [("0", "0"), ("0.5", "0.005"), ("1", "0.01"), ("18", "0.18")])
def test_percentage_units_have_no_heuristic(seeded_shop, admin_emp_id, percentage, rate):
    from core.settings_service import SettingsService
    assert SettingsService.set_setting("default_tax_rate", percentage, actor_id=admin_emp_id)
    assert SettingsService.get_tax_rate() == Decimal(rate)


def test_invalid_settings_cannot_replace_valid_rate(seeded_shop, admin_emp_id):
    from core.settings_service import SettingsService
    assert not SettingsService.set_setting("default_tax_rate", "nan", actor_id=admin_emp_id)
    assert not SettingsService.set_setting("default_tax_rate", "1")
    assert SettingsService.get_tax_rate() == 0


def test_concurrent_same_token_returns_one_committed_sale(seeded_shop, admin_emp_id):
    from core.pos_service import POSTransactionEngine
    gate = threading.Barrier(2)
    def sell():
        gate.wait(timeout=5)
        return POSTransactionEngine.process_checkout(request(admin_emp_id))
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(sell) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert all(r.success for r in results), [r.message for r in results]
    assert results[0].purchase_id == results[1].purchase_id
    assert query(seeded_shop, "SELECT COUNT(*) FROM Purchase")[0] == 1
    assert query(seeded_shop, "SELECT quantity FROM Batch WHERE id=1")[0] == 99


def test_token_cannot_be_reused_for_changed_cart(seeded_shop, admin_emp_id):
    from core.pos_service import POSTransactionEngine
    first = POSTransactionEngine.process_checkout(request(admin_emp_id))
    second = request(admin_emp_id)
    second.cart[0]["qty"] = 2
    rejected = POSTransactionEngine.process_checkout(second)
    assert first.success
    assert not rejected.success and rejected.outcome == "rejected"
    assert query(seeded_shop, "SELECT COUNT(*) FROM Purchase")[0] == 1


def test_matching_batch_active_product_and_authoritative_price(seeded_shop, admin_emp_id):
    from core.pos_service import POSTransactionEngine
    cur = seeded_shop.get_conn().cursor()
    cur.execute("INSERT INTO Products(product_name,company_name,category,price,stock_quantity) VALUES('Other','Co','Cat',20,10)")
    cur.execute("INSERT INTO Batch(product_id,number_of_product,quantity,expiry_date,manufacture_Date,supplier_id) VALUES(2,'B2',10,'2099-12-31','2026-01-01',1)")
    seeded_shop.get_conn().commit()
    bad = request(admin_emp_id)
    bad.cart[0]["batch_id"] = 2
    assert not POSTransactionEngine.process_checkout(bad).success
    bad = request(admin_emp_id)
    bad.cart[0]["price"] = 1
    assert not POSTransactionEngine.process_checkout(bad).success
    cur.execute("UPDATE Products SET is_active=0 WHERE id=1")
    seeded_shop.get_conn().commit()
    assert not POSTransactionEngine.process_checkout(request(admin_emp_id)).success
    assert query(seeded_shop, "SELECT COUNT(*) FROM Purchase")[0] == 0
    assert query(seeded_shop, "SELECT quantity FROM Batch WHERE id=1")[0] == 100


def test_exact_batch_sell_price_is_historical_fact(seeded_shop, admin_emp_id):
    from core.pos_service import POSTransactionEngine
    cur = seeded_shop.get_conn().cursor()
    cur.execute("UPDATE Batch SET sale_price=18 WHERE id=1")
    seeded_shop.get_conn().commit()
    req = request(admin_emp_id)
    req.cart[0]["price"] = 18
    result = POSTransactionEngine.process_checkout(req)
    assert result.success, result.message
    assert query(seeded_shop, "SELECT unit_price,line_subtotal FROM Sales_details WHERE purchase_id=%s", (result.purchase_id,)) == (18, 18)
    assert query(seeded_shop, "SELECT price_with_tax FROM Purchase WHERE id=%s", (result.purchase_id,))[0] == 18


def test_pack_price_rounds_the_selected_unit_not_every_base_unit(seeded_shop, admin_emp_id):
    from core.pos_service import POSTransactionEngine
    cur = seeded_shop.get_conn().cursor()
    cur.execute("UPDATE Products SET price=0.3333,units_per_strip=3 WHERE id=1")
    seeded_shop.get_conn().commit()
    req = request(admin_emp_id)
    req.cart[0].update(qty=10, price=1, unit_code="strip", unit_multiplier=3)
    result = POSTransactionEngine.process_checkout(req)
    assert result.success, result.message
    assert result.total == 10
    assert query(seeded_shop, "SELECT Quantity,line_subtotal,unit_code,display_quantity FROM Sales_details WHERE purchase_id=%s", (result.purchase_id,)) == (30, 10, "strip", 10)
    assert query(seeded_shop, "SELECT quantity FROM Batch WHERE id=1")[0] == 70


def test_cash_requires_matching_counter_and_full_tender(seeded_shop, admin_emp_id):
    from core.cash_session_service import open_session
    from core.pos_service import POSTransactionEngine
    req = request(admin_emp_id, payment_method="Cash", terminal_id="counter1")
    assert not POSTransactionEngine.process_checkout(req).success
    assert open_session(admin_emp_id, 0, terminal_id="counter2")[0]
    assert not POSTransactionEngine.process_checkout(req).success
    assert open_session(admin_emp_id, 0, terminal_id="counter1")[0]
    req.cash_received = 10
    assert not POSTransactionEngine.process_checkout(req).success
    req.cash_received = 20
    result = POSTransactionEngine.process_checkout(req)
    assert result.success, result.message
    assert result.cash_received == 20 and result.change_due == 5


def test_large_discount_needs_consumable_backend_approval(seeded_shop, admin_emp_id):
    from core.manager_auth_service import issue_discount_approval
    from core.pos_service import POSTransactionEngine
    req = request(admin_emp_id, discount=5)
    assert not POSTransactionEngine.process_checkout(req).success
    token, message = issue_discount_approval("admin", "secret123", admin_emp_id, 5, 15)
    assert token, message
    req.manager_approval_token = token
    result = POSTransactionEngine.process_checkout(req)
    assert result.success, result.message
    assert POSTransactionEngine.process_checkout(deepcopy(req)).purchase_id == result.purchase_id
    req.checkout_token = "another-financial-test"
    assert not POSTransactionEngine.process_checkout(req).success


def test_held_completion_is_part_of_sale_commit(seeded_shop, admin_emp_id):
    from core import hold_sale_service
    from models.services import POSModel
    model = POSModel()
    req = request(admin_emp_id)
    draft = {"discount": 1, "payment_method": "Easypaisa", "cash_received": None,
             "selected_customer": {"name": "Walk-in", "id": "WALKIN"}}
    ok, held_id = model.hold_sale("WALKIN", admin_emp_id, req.cart, draft=draft)
    assert ok
    ok, payload = model.recall_sale(held_id, admin_emp_id)
    assert ok and payload["draft"]["discount"] == 1
    req.held_sale_id = held_id
    result = model.process_checkout(req)
    assert result.success, result.message
    assert query(seeded_shop, "SELECT status,purchase_id FROM Hold_Sales WHERE id=%s", (held_id,)) == ("COMPLETED", result.purchase_id)
    hold_sale_service._RECOVERED_STALE_RESUMES = False
    assert all(row[0] != held_id for row in model.held_sales(admin_emp_id))


def test_snapshot_failure_rolls_back_sale_hold_and_stock(seeded_shop, admin_emp_id, monkeypatch):
    from core import receipt_service, hold_sale_service
    from core.pos_service import POSTransactionEngine
    req = request(admin_emp_id)
    ok, held_id = hold_sale_service.hold_sale("WALKIN", admin_emp_id, req.cart)
    assert ok and hold_sale_service.recall_sale(held_id, admin_emp_id)[0]
    req.held_sale_id = held_id
    def fail(*args, **kwargs):
        raise OSError("simulated snapshot failure")
    monkeypatch.setattr(receipt_service, "create_receipt_snapshot", fail)
    result = POSTransactionEngine.process_checkout(req)
    assert not result.success
    assert query(seeded_shop, "SELECT COUNT(*) FROM Purchase")[0] == 0
    assert query(seeded_shop, "SELECT quantity FROM Batch WHERE id=1")[0] == 100
    assert query(seeded_shop, "SELECT status FROM Hold_Sales WHERE id=%s", (held_id,))[0] == "RESUMED"


def test_close_auth_and_cash_mutation_retry(seeded_shop, admin_emp_id):
    from core.cash_session_service import open_session, record_cash_movement, close_session, get_session_cash_summary
    ok, shift = open_session(admin_emp_id, 100)
    assert ok
    assert record_cash_movement(shift, admin_emp_id, "CASH_IN", 25, "change", operation_id="cash-add-1")[0]
    assert record_cash_movement(shift, admin_emp_id, "CASH_IN", 25, "change", operation_id="cash-add-1")[0]
    assert get_session_cash_summary(shift)["expected_cash"] == 125
    assert not close_session(shift, 125)[0]
    closed = close_session(shift, 125, employee_id=admin_emp_id, operation_id="close-1")
    assert closed[0] and closed[1]["discrepancy"] == 0
    assert close_session(shift, 125, employee_id=admin_emp_id, operation_id="close-1")[0]
    assert not record_cash_movement(shift, admin_emp_id, "CASH_IN", 25, "late", operation_id="cash-add-2")[0]


def test_tax_change_requires_review_of_the_displayed_bill(seeded_shop, admin_emp_id):
    from core.settings_service import SettingsService
    from core.pos_service import POSTransactionEngine
    req = request(admin_emp_id, expected_total=15)
    assert SettingsService.set_setting("default_tax_rate", "1", actor_id=admin_emp_id)
    result = POSTransactionEngine.process_checkout(req)
    assert not result.success and result.outcome == "rejected"
    assert "bill changed" in result.message.lower()
    assert query(seeded_shop, "SELECT COUNT(*) FROM Purchase")[0] == 0


def test_sale_and_close_have_one_serialized_cash_boundary(seeded_shop, admin_emp_id):
    from core.cash_session_service import open_session, close_session, get_session_cash_summary
    from core.pos_service import POSTransactionEngine
    ok, shift = open_session(admin_emp_id, 100)
    assert ok
    gate = threading.Barrier(2)
    def sell():
        gate.wait(timeout=5)
        return POSTransactionEngine.process_checkout(request(admin_emp_id, payment_method="Cash"))
    def close():
        gate.wait(timeout=5)
        return close_session(shift, 100, employee_id=admin_emp_id)
    with ThreadPoolExecutor(max_workers=2) as executor:
        sale_future = executor.submit(sell)
        close_future = executor.submit(close)
        sale, closed = sale_future.result(timeout=15), close_future.result(timeout=15)
    assert closed[0]
    expected = 115 if sale.success else 100
    assert closed[1]["expected_cash"] == expected
    assert closed[1]["discrepancy"] == 100 - expected
    assert get_session_cash_summary(shift)["expected_cash"] == expected


@pytest.mark.parametrize("legacy_value,percent,needs_review", [("0", "0", "0"), ("0.10", "10.0", "1"), ("1", "100.0", "1"), ("18", "18", "0")])
def test_upgrade_preserves_raw_tax_and_flags_ambiguous_units(legacy_value, percent, needs_review):
    import sqlite3
    from pathlib import Path
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE Checkout_Request(token TEXT);
        CREATE TABLE Purchase(id INTEGER PRIMARY KEY);
        CREATE TABLE Hold_Sales(id INTEGER PRIMARY KEY);
        CREATE TABLE Sales_details(id INTEGER);
        CREATE TABLE Cash_Register_Session(id INTEGER,employee_id INTEGER,status TEXT);
        CREATE TABLE Pharmacy_Settings(setting_key TEXT PRIMARY KEY,setting_value TEXT NOT NULL);
    """)
    conn.execute("INSERT INTO Pharmacy_Settings VALUES('default_tax_rate',?)", (legacy_value,))
    conn.executescript((Path(__file__).resolve().parents[1] / "migrations/018_financial_integrity.sql").read_text())
    settings = dict(conn.execute("SELECT setting_key,setting_value FROM Pharmacy_Settings"))
    assert Decimal(settings["default_tax_rate"]) == Decimal(percent)
    assert settings["legacy_default_tax_rate"] == legacy_value
    assert settings["tax_rate_review_required"] == needs_review
    assert settings["default_tax_rate_format"] == "percent_v1"
    conn.close()
