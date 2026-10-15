"""Administrative settings/staff authorization regression coverage."""


def _set_session_user(employee_id=None):
    from ui.app.state.session_state import SessionState

    state = SessionState.get_instance()
    state.clear_user()
    if employee_id is not None:
        state.set_user({"id": int(employee_id)})
    return state


def test_first_run_business_settings_allowed_before_any_staff_exists(fresh_db):
    from controllers.settings_controller import SettingsController

    state = _set_session_user()
    try:
        controller = SettingsController()
        assert controller.update({"pharmacy_name": "Bootstrap Pharmacy"}) is True
        assert controller.get("pharmacy_name") == "Bootstrap Pharmacy"
    finally:
        state.clear_user()


def test_viewer_cannot_change_business_settings_or_manage_staff(seeded_shop, admin_emp_id):
    from controllers.settings_controller import SettingsController
    from core import auth_service

    ok, msg = auth_service.create_employee(
        "settingsviewer", "viewer2345", "Read", "Only", occupation="Viewer"
    )
    assert ok, msg
    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT Employee_id FROM Employee WHERE username = 'settingsviewer'")
    viewer_id = int(cur.fetchone()[0])

    state = _set_session_user(viewer_id)
    try:
        controller = SettingsController()
        before = controller.get("default_tax_rate", "0.10")
        assert controller.update({"default_tax_rate": "37.00"}) is False
        assert controller.get("default_tax_rate", "0.10") == before

        ok, message = controller.create_employee(
            "blockedstaff", "blocked234", "Blocked", "Staff", "Cashier"
        )
        assert not ok
        assert "permission" in str(message).lower()
        cur.execute("SELECT COUNT(*) FROM Employee WHERE username = 'blockedstaff'")
        assert int(cur.fetchone()[0]) == 0

        ok, message = controller.create_backup()
        assert not ok
        assert "permission" in str(message).lower()
    finally:
        state.clear_user()


def test_admin_can_change_business_settings_and_manage_staff(seeded_shop, admin_emp_id):
    from controllers.settings_controller import SettingsController

    state = _set_session_user(admin_emp_id)
    try:
        controller = SettingsController()
        assert controller.update({"default_tax_rate": "12.00"}) is True
        assert controller.get("default_tax_rate") == "12.00"

        ok, message = controller.create_employee(
            "newcashier", "cashier234", "New", "Cashier", "Cashier"
        )
        assert ok, message
    finally:
        state.clear_user()
