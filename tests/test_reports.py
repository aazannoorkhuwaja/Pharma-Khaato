"""Reports service: daily sales, expiry alerts, reorder stock, audit log report."""


class TestDailySales:
    def test_empty_day_is_zeroed(self, seeded_shop):
        from core import reports_service
        rep = reports_service.get_daily_sales_report("2099-01-01")
        assert rep is not None
        assert rep["total_transactions"] == 0
        assert rep["total_sales"] == 0.0

    def test_cash_and_credit_split(self, seeded_shop, admin_emp_id):
        from core import pos_service, reports_service
        ok, _ = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 2}],
            payment_method="Cash",
        )
        assert ok
        ok, _ = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Credit",
        )
        assert ok
        rep = reports_service.get_daily_sales_report()
        assert rep["total_transactions"] == 2
        assert abs(rep["total_sales"] - 45.0) < 0.001
        assert abs(rep["cash_sales"] - 30.0) < 0.001
        assert abs(rep["credit_sales"] - 15.0) < 0.001


class TestExpiryAlerts:
    def test_expiring_and_expired_batches_flagged(self, seeded_shop):
        from core import reports_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        # expired batch + soon-expiring batch (both with stock)
        cur.execute(
            "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
            "VALUES (1, 'EXP', 5, '2020-01-01', '2019-01-01', 1)"
        )
        cur.execute(
            "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
            "VALUES (1, 'SOON', 7, '2099-01-15', '2098-12-01', 1)"
        )
        conn.commit()
        alerts = reports_service.get_expiry_alert_report(days_threshold=36500)
        ids = {a["batch_id"] for a in alerts}
        assert 2 in ids and 3 in ids
        exp = next(a for a in alerts if a["batch_id"] == 2)
        assert exp["days_left"] <= 0

    def test_zero_quantity_batch_not_flagged(self, seeded_shop):
        from core import reports_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
            "VALUES (1, 'GONE', 0, '2020-01-01', '2019-01-01', 1)"
        )
        conn.commit()
        alerts = reports_service.get_expiry_alert_report(days_threshold=36500)
        assert all(a["batch_id"] != 2 for a in alerts)

    def test_far_future_batch_outside_threshold(self, seeded_shop):
        from core import reports_service
        alerts = reports_service.get_expiry_alert_report(days_threshold=30)
        assert all(a["batch_id"] != 1 for a in alerts)


class TestReorderStock:
    def test_low_stock_flagged(self, seeded_shop):
        from core import reports_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE Products SET stock_quantity=5 WHERE id=1")
        conn.commit()
        rows = reports_service.get_reorder_stock_report()
        match = [r for r in rows if r["product_id"] == 1]
        assert match and match[0]["stock_quantity"] == 5

    def test_healthy_stock_not_flagged(self, seeded_shop):
        from core import reports_service
        rows = reports_service.get_reorder_stock_report()
        assert all(r["product_id"] != 1 for r in rows)


class TestAuditReport:
    def test_returns_login_events(self, seeded_shop, admin_emp_id):
        from core import auth_service, reports_service
        auth_service.login_user("admin", "secret123")  # writes audit event
        rep = reports_service.get_audit_log_report(limit=10)
        assert any(e["event_type"] == "USER_LOGIN_SUCCESS" for e in rep)
