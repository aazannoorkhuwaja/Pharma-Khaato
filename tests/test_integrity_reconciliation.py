"""Accounting reconciliation: real damage must be noticed, healthy data must not be.

The point of these checks is to be trustworthy in both directions. A check that
never fires is decoration, and a check that fires on a healthy shop trains the
owner to ignore it. So every test here either builds a shop the way the product
builds it — discounted cash sale, credit sale, cash repayment, cash shift — and
demands silence, or damages one stored fact and demands that the exact check
responsible speaks up.
"""

import pytest


@pytest.fixture()
def busy_shop(seeded_shop, admin_emp_id, cash_shift):
    """A shop that has taken a discounted sale, a credit sale and a repayment."""
    from core.credit_payment_service import record_customer_payment
    from core.pos_service import confirm_sale

    conn = seeded_shop.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Customers (id_card_number, first_name, last_name, Email_Address, city, registration_date) "
        "VALUES ('3520212345671', 'Credit', 'Customer', 'N/A', 'Karachi', '2026-01-01')"
    )
    conn.commit()

    cart = [{"prod_id": 1, "name": "TestMed", "price": 15.0, "batch_id": 1, "qty": 2, "subtotal": 30.0}]
    # The discounted sale stays below the manager-approval threshold while still
    # moving the recorded discount, so the sale-arithmetic identity is exercised.
    for target, total, discount, method in (
        ("WALKIN", 30.0, 0.0, "Cash"),
        ("WALKIN", 28.0, 2.0, "Cash"),
        ("3520212345671", 30.0, 0.0, "Khatoo Credit"),
    ):
        ok, message = confirm_sale(target, admin_emp_id, cart, total=total, discount=discount, payment_method=method)
        assert ok, message

    ok, message, _meta = record_customer_payment(
        "3520212345671", 10.0, admin_emp_id, "Cash", "part payment", operation_id="integrity-fixture"
    )
    assert ok, message
    return seeded_shop


def _tamper(db, statements):
    """Change stored facts behind the application's back, as a restore or an edit would."""
    conn = db.get_conn()
    cur = conn.cursor()
    for sql in statements:
        cur.execute(sql)
    conn.commit()


def _checks(report):
    return {finding["check"] for finding in report["findings"]}


def test_healthy_shop_reports_no_drift(busy_shop):
    from core.integrity_service import format_findings, reconcile

    report = reconcile()
    assert report["findings"] == [], format_findings(report)
    assert report["ok"] is True
    assert report["checks_run"] == 6


def test_stock_divergence_is_detected(busy_shop):
    from core.integrity_service import reconcile

    _tamper(busy_shop, ["UPDATE Products SET stock_quantity = stock_quantity + 1 WHERE id = 1"])
    assert "stock_total_vs_batches" in _checks(reconcile())


def test_sale_arithmetic_damage_is_detected(busy_shop):
    from core.integrity_service import reconcile

    _tamper(busy_shop, ["UPDATE Purchase SET total_price = total_price + 5 WHERE id = 2"])
    assert "sale_line_and_tax_arithmetic" in _checks(reconcile())


def test_credit_balance_larger_than_its_sale_is_detected(busy_shop):
    from core.integrity_service import reconcile

    _tamper(busy_shop, ["UPDATE Customer_Khatoo SET amount_due = amount_due + 99"])
    assert "customer_credit_ledger" in _checks(reconcile())


def test_negative_credit_balance_is_detected(busy_shop):
    from core.integrity_service import reconcile

    _tamper(busy_shop, ["UPDATE Customer_Khatoo SET amount_due = -5"])
    assert "customer_credit_ledger" in _checks(reconcile())


def test_refund_beyond_the_sale_value_is_detected(busy_shop):
    from core.integrity_service import reconcile

    _tamper(
        busy_shop,
        [
            "INSERT INTO Customer_Returns "
            "(purchase_id, customer_id, employee_id, refund_amount, reason, return_date, return_time, "
            " refund_method, refund_status) "
            "SELECT id, 'WALKIN', employee_id, price_with_tax + 100, 'Damage test', '2026-01-01', '10:00:00', "
            "       'Cash', 'RECORDED' FROM Purchase ORDER BY id LIMIT 1"
        ],
    )
    assert "refunds_within_sale_value" in _checks(reconcile())


def test_partial_refund_within_the_sale_value_is_not_reported(busy_shop):
    from core.integrity_service import reconcile

    _tamper(
        busy_shop,
        [
            "INSERT INTO Customer_Returns "
            "(purchase_id, customer_id, employee_id, refund_amount, reason, return_date, return_time, "
            " refund_method, refund_status) "
            "SELECT id, 'WALKIN', employee_id, 1.0, 'Small refund', '2026-01-01', '10:00:00', "
            "       'Cash', 'RECORDED' FROM Purchase ORDER BY id LIMIT 1"
        ],
    )
    assert reconcile()["ok"] is True


def test_closed_shift_that_no_longer_reconciles_is_detected(seeded_shop, admin_emp_id, cash_shift):
    from core.cash_session_service import close_session
    from core.integrity_service import reconcile

    assert reconcile()["ok"] is True
    ok, result = close_session(cash_shift, 0.0, notes="reconciliation test", employee_id=admin_emp_id)
    assert ok, result
    assert reconcile()["ok"] is True, "a closed shift with no activity must still reconcile"

    _tamper(seeded_shop, [f"UPDATE Cash_Register_Session SET expected_cash_system = expected_cash_system + 50 WHERE id = {cash_shift}"])
    assert "closed_shift_cash_reconciliation" in _checks(reconcile())


def test_orphan_row_is_detected(seeded_shop):
    """A hand-edited or partially restored file is exactly what this guards."""
    from core.integrity_service import reconcile

    conn = seeded_shop.get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")
    cur.execute("INSERT INTO Sales_details (purchase_id, batch_id, Quantity) VALUES (99999, 1, 1)")
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    assert "orphan_rows" in _checks(reconcile())


def test_launch_self_check_surfaces_reconciliation(seeded_shop):
    from core.readiness_service import run_readiness_checks

    report = run_readiness_checks()
    check = next(
        (item for item in report["checks"] if item["name"] == "Business data reconciliation"), None
    )
    assert check is not None, "the self-check does not run reconciliation"
    assert check["ok"] is True
    assert report["ok"] is True


def test_launch_self_check_fails_on_drift(seeded_shop):
    from core.readiness_service import run_readiness_checks

    _tamper(seeded_shop, ["UPDATE Products SET stock_quantity = stock_quantity + 1 WHERE id = 1"])
    report = run_readiness_checks()
    check = next(
        (item for item in report["checks"] if item["name"] == "Business data reconciliation"), None
    )
    assert check is not None and check["ok"] is False
    assert "stock_total_vs_batches" in check["detail"]
    assert report["ok"] is False
