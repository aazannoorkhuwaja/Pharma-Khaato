"""Real-world regression coverage for returns, permissions, and held sales."""


def _cash_sale(admin_emp_id, qty=2, payment_method="Cash", customer_id=None):
    from core import pos_service
    ok, msg = pos_service.confirm_sale(
        customer_id,
        admin_emp_id,
        [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": qty}],
        payment_method=payment_method,
    )
    assert ok, msg
    return int(msg.split("Sale #")[1].split(" ")[0])


def test_held_sale_resume_is_non_destructive(seeded_shop, admin_emp_id):
    from core import hold_sale_service

    cart = [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 2}]
    ok, hold_id = hold_sale_service.hold_sale("WALKIN", admin_emp_id, cart)
    assert ok

    rows = hold_sale_service.get_held_sales(admin_emp_id)
    assert [row[0] for row in rows] == [hold_id]

    ok, resumed = hold_sale_service.recall_sale(hold_id, admin_emp_id)
    assert ok and resumed["cart"][0]["qty"] == 2

    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT status, cart_json FROM Hold_Sales WHERE id = %s", (hold_id,))
    status, cart_json = cur.fetchone()
    assert status == "RESUMED"
    assert "TestMed" in cart_json

    # Re-holding updates the same durable row instead of creating a duplicate.
    resumed["cart"][0]["qty"] = 1
    ok, same_id = hold_sale_service.rehold_sale(
        hold_id, "WALKIN", admin_emp_id, resumed["cart"], "customer stepped away"
    )
    assert ok and same_id == hold_id
    cur.execute("SELECT COUNT(*), status FROM Hold_Sales WHERE id = %s", (hold_id,))
    count, status = cur.fetchone()
    assert count == 1 and status == "HELD"


def test_stale_resumed_hold_recovers_after_simulated_restart(seeded_shop, admin_emp_id):
    from core import hold_sale_service

    cart = [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}]
    ok, hold_id = hold_sale_service.hold_sale("WALKIN", admin_emp_id, cart)
    assert ok
    ok, _ = hold_sale_service.recall_sale(hold_id, admin_emp_id)
    assert ok

    # Simulate a fresh process: its one-time recovery changes stale RESUMED to HELD.
    hold_sale_service._RECOVERED_STALE_RESUMES = False
    rows = hold_sale_service.get_held_sales(admin_emp_id)
    assert hold_id in [row[0] for row in rows]


def test_cash_return_reduces_physical_drawer_and_restocks(seeded_shop, admin_emp_id):
    from core import cash_session_service, return_service

    ok, session_id = cash_session_service.open_session(admin_emp_id, 500.0)
    assert ok
    purchase_id = _cash_sale(admin_emp_id, qty=2, payment_method="Cash")
    before = cash_session_service.get_session_cash_summary(session_id)
    assert before["expected_cash"] == 530.0

    ok, result = return_service.process_return(
        purchase_id,
        [{"batch_id": 1, "qty": 1, "price": 999999.0}],  # forged price must be ignored
        admin_emp_id,
        reason="Customer changed mind",
        condition="SELLABLE",
    )
    assert ok, result
    assert result["refund_amount"] == 15.0

    after = cash_session_service.get_session_cash_summary(session_id)
    assert after["refunds"] == 15.0
    assert after["expected_cash"] == 515.0

    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT quantity FROM Batch WHERE id = 1")
    assert cur.fetchone()[0] == 99
    cur.execute("SELECT payment_method, amount FROM Refund_Transaction ORDER BY id DESC LIMIT 1")
    method, amount = cur.fetchone()
    assert method == "Cash" and float(amount) == 15.0


def test_digital_return_never_changes_drawer(seeded_shop, admin_emp_id):
    from core import return_service

    purchase_id = _cash_sale(admin_emp_id, qty=1, payment_method="Easypaisa")
    ok, result = return_service.process_return(
        purchase_id,
        [{"batch_id": 1, "qty": 1}],
        admin_emp_id,
        condition="DAMAGED",
    )
    assert ok, result

    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT payment_method, session_id FROM Refund_Transaction ORDER BY id DESC LIMIT 1")
    method, session_id = cur.fetchone()
    assert method == "Easypaisa"
    assert session_id is None
    cur.execute("SELECT COUNT(*) FROM Cash_Movement")
    assert cur.fetchone()[0] == 0


def test_credit_return_reduces_due_then_refunds_actual_collection_tender(seeded_shop, admin_emp_id):
    from core import cash_session_service, credit_payment_service, customer_service, return_service

    ok, _ = customer_service.register_customer(
        "3520212345678", "Return", "Customer", "N/A", "Test City"
    )
    assert ok
    purchase_id = _cash_sale(
        admin_emp_id,
        qty=2,
        payment_method="Khatoo Credit",
        customer_id="3520212345678",
    )

    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT id FROM Customer_Khatoo WHERE purchase_id = %s", (purchase_id,))
    ledger_id = cur.fetchone()[0]

    ok, session_id = cash_session_service.open_session(admin_emp_id, 500.0)
    assert ok
    ok, msg = credit_payment_service.record_credit_payment(
        ledger_id, 10.0, admin_emp_id, "Cash"
    )
    assert ok, msg
    assert cash_session_service.get_session_cash_summary(session_id)["expected_cash"] == 510.0

    # First returned unit reduces outstanding debt only; no cash leaves drawer.
    ok, first = return_service.process_return(
        purchase_id, [{"batch_id": 1, "qty": 1}], admin_emp_id, condition="SELLABLE"
    )
    assert ok, first
    assert cash_session_service.get_session_cash_summary(session_id)["expected_cash"] == 510.0

    cur.execute("SELECT amount_due, amount_paid FROM Customer_Khatoo WHERE id = %s", (ledger_id,))
    due, paid = cur.fetchone()
    assert float(due) == 5.0 and float(paid) == 10.0

    # Final unit clears the last Rs.5 due and refunds the Rs.10 previously paid in cash.
    ok, second = return_service.process_return(
        purchase_id, [{"batch_id": 1, "qty": 1}], admin_emp_id, condition="SELLABLE"
    )
    assert ok, second
    summary = cash_session_service.get_session_cash_summary(session_id)
    assert summary["refunds"] == 10.0
    assert summary["expected_cash"] == 500.0
    cur.execute("SELECT amount_due, amount_paid FROM Customer_Khatoo WHERE id = %s", (ledger_id,))
    due, paid = cur.fetchone()
    assert float(due) == 0.0 and float(paid) == 0.0


def test_cashier_cannot_process_returns_even_if_service_called_directly(seeded_shop, admin_emp_id):
    from core import auth_service, return_service

    purchase_id = _cash_sale(admin_emp_id, qty=1)
    ok, msg = auth_service.create_employee(
        "cashier", "cashier123", "Counter", "Staff", occupation="Salesman"
    )
    assert ok, msg
    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT Employee_id FROM Employee WHERE username = 'cashier'")
    cashier_id = cur.fetchone()[0]

    ok, msg = return_service.process_return(
        purchase_id, [{"batch_id": 1, "qty": 1}], cashier_id
    )
    assert not ok
    assert "permission" in str(msg).lower()
