"""POS checkout: atomicity, FEFO, expiry guard, oversell guard, CNIC normalization."""


class TestPOS:
    def test_cash_sale_deducts_stock(self, seeded_shop, admin_emp_id, cash_shift):
        from core import pos_service
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 3}],
            payment_method="Cash",
        )
        assert ok, msg
        cur = seeded_shop.get_conn().cursor()
        cur.execute("SELECT stock_quantity FROM Products WHERE id=1")
        assert cur.fetchone()[0] == 97
        cur.execute("SELECT quantity FROM Batch WHERE id=1")
        assert cur.fetchone()[0] == 97

    def test_expired_batch_blocked(self, seeded_shop, admin_emp_id):
        from core import pos_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
            "VALUES (1, 'OLD', 50, '2020-01-01', '2019-01-01', 1)"
        )
        conn.commit()
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "batch_id": 2, "price": 15.0, "qty": 5}],
            payment_method="Cash",
        )
        assert not ok and "expired" in msg.lower()

    def test_oversell_rejected(self, seeded_shop, admin_emp_id):
        from core import pos_service
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 99999}],
            payment_method="Cash",
        )
        assert not ok

    def test_negative_discount_rejected(self, seeded_shop, admin_emp_id):
        from core import pos_service
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            discount=-5.0, payment_method="Cash",
        )
        assert not ok

    def test_cnic_normalized_on_credit_sale(self, seeded_shop, admin_emp_id):
        """Regression: dashed CNIC stored raw made debt invisible."""
        from core import pos_service, db_engine, customer_service
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Customers (id_card_number, first_name, last_name, registration_date) "
            "VALUES ('1234567890123', 'Ali', 'Khan', '2026-01-01')"
        )
        cur.execute("UPDATE Products SET price=100 WHERE id=1")
        conn.commit()
        ok, msg = pos_service.confirm_sale(
            "12345-6789012-3", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 100.0, "qty": 4}],
            payment_method="Khatoo Credit",
        )
        assert ok, msg
        debt = customer_service.get_customer_total_debt("1234567890123")
        assert float(debt) == 400.00

    def test_credit_requires_registered_customer(self, seeded_shop, admin_emp_id):
        from core import pos_service
        ok, msg = pos_service.confirm_sale(
            "9999912345678", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Khatoo Credit",
        )
        assert not ok

    def test_invalid_cnic_rejected(self, seeded_shop, admin_emp_id):
        from core import pos_service
        ok, msg = pos_service.confirm_sale(
            "BAD-ID", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Cash",
        )
        assert not ok and "customer" in msg.lower()

    def test_walkin_defaults(self, seeded_shop, admin_emp_id, cash_shift):
        from core import pos_service
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Cash",
        )
        assert ok


class TestCreditLimit:
    def test_limit_enforced_with_real_debt(self, seeded_shop, admin_emp_id):
        """Regression: debt was undercounted to zero, defeating the cap."""
        from core import pos_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Customers (id_card_number, first_name, last_name, registration_date) "
            "VALUES ('1234567890123', 'Ali', 'Khan', '2026-01-01')"
        )
        conn.commit()
        cur.execute("UPDATE Products SET price=1000 WHERE id=1")
        conn.commit()
        # Rs 4,000 credit sale succeeds
        ok, _ = pos_service.confirm_sale(
            "12345-6789012-3", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 1000.0, "qty": 4}],
            payment_method="Khatoo Credit",
        )
        assert ok
        cur.execute("UPDATE Products SET price=5500 WHERE id=1")
        conn.commit()
        # Rs 22,000 more would exceed the default Rs 25,000 cap — must block
        ok2, msg2 = pos_service.confirm_sale(
            "12345-6789012-3", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 5500.0, "qty": 4}],
            payment_method="Khatoo Credit",
        )
        assert not ok2 and "credit limit" in msg2.lower()


def test_khatoo_payment_method_aliases_are_normalized():
    from core.pos_service import _normalize_payment_method

    for alias in ("Khatoo Credit", "Credit (Khatoo)", "khatoo"):
        canonical, accounting = _normalize_payment_method(alias)
        assert canonical == "Khatoo Credit"
        assert accounting == "Credit"
