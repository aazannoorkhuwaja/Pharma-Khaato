"""Authentication: hashing, lockout persistence, legacy rejection."""


class TestAuth:
    def test_register_and_login(self, seeded_shop):
        from core import auth_service
        res = auth_service.login_user("admin", "secret123")
        assert res is not None
        emp_id, fname, lname, occupation = res
        assert fname == "Test"

    def test_wrong_password_fails(self, seeded_shop):
        from core import auth_service
        assert auth_service.login_user("admin", "wrongpw") is None

    def test_plaintext_credential_rejected(self, seeded_shop):
        from core import auth_service, db_engine
        conn = db_engine.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE Employee SET password='secret123' WHERE username='admin'")
        conn.commit()
        assert auth_service.login_user("admin", "secret123") is None

    def test_lockout_persists_in_db(self, seeded_shop):
        from core import auth_service, db_engine
        ok, msg = auth_service.create_employee(
            "cashier", "goodpass1", "C", "A", occupation="Salesman"
        )
        assert ok, msg
        for _ in range(5):
            auth_service.login_user("cashier", "badpw")
        with __import__("pytest").raises(PermissionError):
            auth_service.login_user("cashier", "badpw")
        cur = db_engine.get_conn().cursor()
        cur.execute(
            "SELECT failed_attempts FROM Login_Lockout WHERE username='cashier'"
        )
        row = cur.fetchone()
        assert row and row[0] >= 5

    def test_lockout_survives_connection_reset(self, seeded_shop):
        from core import auth_service, db_engine
        for _ in range(5):
            auth_service.login_user("admin", "nope")
        db_engine.reset_thread_connections()  # simulates app restart
        try:
            auth_service.login_user("admin", "nope")
            raised = False
        except PermissionError:
            raised = True
        assert raised

    def test_has_registered_employees_true(self, seeded_shop):
        from core.auth_service import has_registered_employees
        assert has_registered_employees() is True

    def test_duplicate_username_rejected(self, seeded_shop):
        from core import auth_service
        ok, msg = auth_service.register_initial_admin("admin", "pw123456", "X", "Y")
        assert ok is False

    def test_initial_admin_bootstrap_cannot_create_second_admin(self, seeded_shop):
        from core import auth_service

        ok, msg = auth_service.register_initial_admin(
            "backdooradmin", "another123", "Second", "Admin"
        )
        assert not ok
        assert "setup" in str(msg).lower()
        cur = seeded_shop.get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM Employee WHERE username='backdooradmin'")
        assert int(cur.fetchone()[0]) == 0


def test_lower_cost_pbkdf2_is_upgraded_after_login(seeded_shop):
    from core import auth_service, db_engine

    old_hash = auth_service._hash_password("secret123", iterations=100_000)
    conn = db_engine.get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE Employee SET password=%s WHERE username=%s", (old_hash, "admin"))
    conn.commit()

    assert auth_service.login_user("admin", "secret123") is not None
    cur.execute("SELECT password FROM Employee WHERE username=%s", ("admin",))
    upgraded = cur.fetchone()[0]
    assert upgraded.startswith("pbkdf2:sha256:600000$")
