"""Regression coverage for tender accounting and fast search paths."""

from core.business_time import business_date


def _sell(pos_service, admin_emp_id, payment_method, qty=1):
    ok, msg = pos_service.confirm_sale(
        None,
        admin_emp_id,
        [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": qty}],
        payment_method=payment_method,
    )
    assert ok, msg


def test_digital_tenders_do_not_enter_physical_drawer(seeded_shop, admin_emp_id):
    from core import cash_session_service, pos_service

    ok, session_id = cash_session_service.open_session(admin_emp_id, 1000.0)
    assert ok
    _sell(pos_service, admin_emp_id, "Cash")
    _sell(pos_service, admin_emp_id, "Credit Card")
    _sell(pos_service, admin_emp_id, "Easypaisa")
    _sell(pos_service, admin_emp_id, "JazzCash")

    summary = cash_session_service.get_session_cash_summary(session_id)
    assert summary["cash_sales"] == 15.0
    assert summary["expected_cash"] == 1015.0


def test_reports_keep_each_tender_separate(seeded_shop, admin_emp_id, cash_shift):
    from core import pos_service, reports_service

    _sell(pos_service, admin_emp_id, "Cash")
    _sell(pos_service, admin_emp_id, "Credit Card")
    _sell(pos_service, admin_emp_id, "Easypaisa")
    _sell(pos_service, admin_emp_id, "JazzCash")

    report = reports_service.get_daily_sales_report(business_date().isoformat())
    assert report["total_sales"] == 60.0
    assert report["cash_sales"] == 15.0
    assert report["card_sales"] == 15.0
    assert report["easypaisa_sales"] == 15.0
    assert report["jazzcash_sales"] == 15.0
    assert report["digital_sales"] == 45.0


def test_cash_credit_collection_enters_open_drawer(seeded_shop, admin_emp_id):
    from core import cash_session_service, credit_payment_service, customer_service, pos_service

    ok, _ = customer_service.register_customer(
        "3520212345671", "Credit", "Customer", "N/A", "Test City"
    )
    assert ok
    ok, msg = pos_service.confirm_sale(
        "3520212345671",
        admin_emp_id,
        [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 2}],
        payment_method="Khatoo Credit",
    )
    assert ok, msg

    conn = seeded_shop.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM Customer_Khatoo ORDER BY id DESC LIMIT 1")
    ledger_id = cur.fetchone()[0]

    ok, session_id = cash_session_service.open_session(admin_emp_id, 500.0)
    assert ok
    ok, msg = credit_payment_service.record_credit_payment(
        ledger_id, 10.0, admin_emp_id, "Cash", "Partial payment"
    )
    assert ok, msg

    summary = cash_session_service.get_session_cash_summary(session_id)
    assert summary["cash_credit_collections"] == 10.0
    assert summary["expected_cash"] == 510.0

    cur.execute("SELECT amount, payment_method, session_id FROM Credit_Payment ORDER BY id DESC LIMIT 1")
    amount, method, stored_session = cur.fetchone()
    assert float(amount) == 10.0
    assert method == "Cash"
    assert stored_session == session_id


def test_cash_credit_collection_requires_open_shift(seeded_shop, admin_emp_id):
    from core import credit_payment_service, customer_service, pos_service

    ok, _ = customer_service.register_customer(
        "3520212345672", "No", "Shift", "N/A", "Test City"
    )
    assert ok
    ok, msg = pos_service.confirm_sale(
        "3520212345672",
        admin_emp_id,
        [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
        payment_method="Khatoo Credit",
    )
    assert ok, msg

    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT id FROM Customer_Khatoo ORDER BY id DESC LIMIT 1")
    ledger_id = cur.fetchone()[0]
    ok, msg = credit_payment_service.record_credit_payment(
        ledger_id, 5.0, admin_emp_id, "Cash"
    )
    assert not ok
    assert "cash shift" in msg.lower()


def test_fast_product_search_returns_total_sellable_stock(seeded_shop):
    from core.product_search_service import search_sellable_products

    rows = search_sellable_products("TestMed")
    assert rows
    product_id, name, price, batch_id, sellable_stock, expiry = rows[0][:6]
    assert product_id == 1
    assert name == "TestMed"
    assert float(price) == 15.0
    assert batch_id == 1
    assert int(sellable_stock) == 100
    assert str(expiry).startswith("2099-")
