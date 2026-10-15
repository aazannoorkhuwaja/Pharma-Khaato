"""Cash session lifecycle: open/move/expected/close edge cases."""


class TestOpenSession:
    def test_negative_float_rejected(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, msg = css.open_session(admin_emp_id, opening_cash=-5)
        assert not ok

    def test_duplicate_open_rejected(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, _ = css.open_session(admin_emp_id, 100)
        assert ok
        ok2, msg2 = css.open_session(admin_emp_id, 50)
        assert not ok2 and "already" in str(msg2).lower()


class TestMovements:
    def test_invalid_movement_type_rejected(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, _ = css.open_session(admin_emp_id, 100)
        assert ok
        ok1, _ = css.record_cash_movement(1, admin_emp_id, "PAYOUT", 10)
        assert not ok1

    def test_nonpositive_amount_rejected(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, _ = css.open_session(admin_emp_id, 100)
        assert ok
        assert not css.record_cash_movement(1, admin_emp_id, "CASH_IN", 0)[0]
        assert not css.record_cash_movement(1, admin_emp_id, "CASH_IN", -5)[0]

    def test_cash_in_out_change_expected_cash(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, sid = css.open_session(admin_emp_id, 500)
        assert ok
        ok1, _ = css.record_cash_movement(sid, admin_emp_id, "CASH_OUT", 120.00, "supplier payment")
        ok2, _ = css.record_cash_movement(sid, admin_emp_id, "CASH_IN", 30.50, "found cash")
        assert ok1 and ok2
        _opening, _sales, expected = css.calculate_expected_cash(sid)
        assert abs(expected - (500 - 120 + 30.5)) < 0.001


class TestCloseSession:
    def test_close_with_shortage(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, sid = css.open_session(admin_emp_id, 200)
        assert ok
        # Count Rs.190 — Rs.10 shortage must be accepted and session closed.
        ok_c, result = css.close_session(
            sid, 190.0, notes="short test", employee_id=admin_emp_id
        )
        assert ok_c, result
        assert css.get_active_session(admin_emp_id) is None

    def test_close_requires_acting_employee(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, sid = css.open_session(admin_emp_id, 200)
        assert ok
        ok_c, message = css.close_session(sid, 200.0)
        assert not ok_c
        assert "sign in" in str(message).lower()
        assert css.get_active_session(admin_emp_id) is not None

    def test_staff_cannot_close_another_staff_members_shift(self, seeded_shop, admin_emp_id):
        from core import auth_service, cash_session_service as css

        ok, msg = auth_service.create_employee(
            "cashshift2", "cashshift234", "Second", "Cashier", occupation="Cashier"
        )
        assert ok, msg
        cur = seeded_shop.get_conn().cursor()
        cur.execute("SELECT Employee_id FROM Employee WHERE username = 'cashshift2'")
        other_id = int(cur.fetchone()[0])

        ok, sid = css.open_session(admin_emp_id, 200)
        assert ok
        ok_c, message = css.close_session(
            sid, 200.0, notes="wrong actor", employee_id=other_id
        )
        assert not ok_c
        assert "another staff member" in str(message).lower()
        assert css.get_active_session(admin_emp_id) is not None

    def test_expected_equals_opening_when_no_activity(self, seeded_shop, admin_emp_id):
        from core import cash_session_service as css
        ok, sid = css.open_session(admin_emp_id, 300)
        assert ok
        _o, _s, expected = css.calculate_expected_cash(sid)
        assert abs(expected - 300) < 0.001
