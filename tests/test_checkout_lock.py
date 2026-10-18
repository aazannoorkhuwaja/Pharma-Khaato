"""Regression: checkout lock must release on early-return validation failures."""


class TestCheckoutLock:
    def test_lock_released_after_failed_checkout(self, seeded_shop, admin_emp_id, cash_shift):
        from core import pos_service
        # Fail once (invalid CNIC — early return before the old try/finally)
        ok1, _ = pos_service.confirm_sale(
            "BAD-ID", admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Cash",
        )
        assert not ok1
        # The next checkout MUST NOT be deadlocked
        ok2, msg2 = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Cash",
        )
        assert ok2, f"Checkout deadlocked after prior failure: {msg2}"

    def test_lock_released_after_exception(self, seeded_shop, admin_emp_id, cash_shift):
        from core import pos_service
        pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 99999}],
            payment_method="Cash",
        )
        ok, msg = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 1}],
            payment_method="Cash",
        )
        assert ok, f"Checkout deadlocked after exception: {msg}"
