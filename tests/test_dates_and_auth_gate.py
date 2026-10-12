"""Date normalization + FEFO correctness with loose date input."""


class TestExpiryDates:
    def test_loose_date_normalized_on_add(self, seeded_shop):
        from core import inventory_service, db_engine
        ok, msg = inventory_service.add_batch(1, 1, 10, "2027-1-5")
        assert ok, msg
        cur = db_engine.get_conn().cursor()
        cur.execute("SELECT expiry_date FROM Batch ORDER BY id DESC LIMIT 1")
        assert cur.fetchone()[0] == "2027-01-05"

    def test_slash_date_accepted(self, seeded_shop):
        from core import inventory_service
        ok, msg = inventory_service.add_batch(1, 1, 10, "2027/06/15")
        assert ok, msg

    def test_past_expiry_rejected(self, seeded_shop):
        from core import inventory_service
        ok, msg = inventory_service.add_batch(1, 1, 10, "2020-01-01")
        assert not ok

    def test_fefo_uses_earliest_real_expiry(self, seeded_shop, admin_emp_id):
        """Regression: non-padded dates ('2027-1-5') broke FEFO ordering."""
        from core import pos_service, inventory_service, db_engine
        # batch 2: real expiry 2098 (padded), batch 3: 2097 via loose input
        inventory_service.add_batch(1, 1, 40, "2097-7-1")
        db_engine.get_conn().commit()
        ok, _ = pos_service.confirm_sale(
            None, admin_emp_id,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 5}],
            payment_method="Cash",
        )
        assert ok
        cur = db_engine.get_conn().cursor()
        cur.execute("SELECT id, quantity FROM Batch ORDER BY id")
        rows = {bid: qty for bid, qty in cur.fetchall()}
        # FEFO must consume the 2097 batch (the newly added one), not the padded 2099 seed batch (id 1)
        new_batch_id = max(rows)
        assert rows[new_batch_id] == 35 and rows[1] == 100


class TestManagerAuth:
    def test_small_discount_allowed_without_approval(self):
        from core.manager_auth_service import enforce_discount_policy
        ok, _ = enforce_discount_policy(5.0, 100.0)  # 5% < 10%
        assert ok

    def test_large_discount_requires_manager(self):
        from core.manager_auth_service import enforce_discount_policy
        ok, msg = enforce_discount_policy(20.0, 100.0)  # 20% > 10%
        assert not ok and "authorization" in msg.lower()

    def test_manager_credentials_authorize(self, seeded_shop):
        from core.manager_auth_service import enforce_discount_policy
        ok, msg = enforce_discount_policy(20.0, 100.0, "admin", "secret123")
        assert ok

    def test_non_manager_rejected(self, seeded_shop):
        from core import auth_service
        from core.manager_auth_service import enforce_discount_policy
        auth_service.create_employee("clerk", "clerkpw", "C", "K", occupation="Salesman")
        ok, msg = enforce_discount_policy(20.0, 100.0, "clerk", "clerkpw")
        assert not ok

    def test_wrong_password_rejected(self, seeded_shop):
        from core.manager_auth_service import enforce_discount_policy
        ok, _ = enforce_discount_policy(20.0, 100.0, "admin", "wrongpw")
        assert not ok
