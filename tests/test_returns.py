"""Regression tests for sale-return bugs."""


class TestSaleReturn:
    def _make_credit_sale(self, seeded_shop, admin_emp_id):
        from core import pos_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO Customers (id_card_number, first_name, last_name, registration_date) "
            "VALUES ('1234567890123', 'Ali', 'Khan', '2026-01-01')"
        )
        conn.commit()
        ok, msg = pos_service.confirm_sale(
            "12345-6789012-3", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 100.0, "qty": 10}],
            payment_method="Khatoo Credit",
        )
        assert ok, msg
        return int(msg.split("Sale #")[1].split(" ")[0])

    def test_return_reduces_khatoo_debt(self, seeded_shop, admin_emp_id):
        """Regression: credit-sale returns left ledger debt unchanged."""
        from core import pos_service, customer_service
        pid = self._make_credit_sale(seeded_shop, admin_emp_id)
        assert float(customer_service.get_customer_total_debt('1234567890123')) == 1000.00
        ok, msg = pos_service.process_sale_return(
            pid, [{"batch_id": 1, "qty": 5, "prod_id": 1, "price": 100.0}],
            employee_id=admin_emp_id,
        )
        assert ok, msg
        assert float(customer_service.get_customer_total_debt('1234567890123')) == 500.00

    def test_over_return_blocked(self, seeded_shop, admin_emp_id):
        """Regression: returns were unvalidated against sold quantity."""
        from core import pos_service
        pid = self._make_credit_sale(seeded_shop, admin_emp_id)
        ok, msg = pos_service.process_sale_return(
            pid, [{"batch_id": 1, "qty": 99, "prod_id": 1, "price": 100.0}],
            employee_id=admin_emp_id,
        )
        assert not ok and "remain returnable" in msg

    def test_double_return_capped(self, seeded_shop, admin_emp_id):
        from core import pos_service
        pid = self._make_credit_sale(seeded_shop, admin_emp_id)
        ok1, _ = pos_service.process_sale_return(
            pid, [{"batch_id": 1, "qty": 8, "prod_id": 1, "price": 100.0}],
            employee_id=admin_emp_id,
        )
        assert ok1
        ok2, msg2 = pos_service.process_sale_return(
            pid, [{"batch_id": 1, "qty": 5, "prod_id": 1, "price": 100.0}],
            employee_id=admin_emp_id,
        )
        assert not ok2

    def test_return_unknown_purchase(self, seeded_shop, admin_emp_id):
        from core import pos_service
        ok, msg = pos_service.process_sale_return(
            424242, [{"batch_id": 1, "qty": 1, "prod_id": 1, "price": 15.0}],
            employee_id=admin_emp_id,
        )
        assert not ok and "not found" in msg


class TestTaxPipeline:
    def test_percentage_setting_drives_receipt_tax(self, seeded_shop, admin_emp_id):
        from core import pos_service, db_engine
        from core.settings_service import SettingsService
        SettingsService.set_setting("default_tax_rate", "18.0")
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 100.0, "qty": 10}],
            payment_method="Cash",
        )
        assert ok
        cur = db_engine.get_conn().cursor()
        cur.execute("SELECT total_price, price_with_tax FROM Purchase ORDER BY id DESC LIMIT 1")
        net, gross = cur.fetchone()
        assert abs(gross - net * 1.18) < 0.05
