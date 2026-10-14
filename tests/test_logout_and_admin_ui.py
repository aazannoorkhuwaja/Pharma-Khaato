"""Regression coverage for authentication exit flow and admin action tables."""

from pathlib import Path


def test_sign_out_button_clears_session_when_clicked(qapp, fresh_db):
    from ui.app.main_window import MainWindow
    from ui.app.state.session_state import SessionState

    state = SessionState.get_instance()
    state.clear_user()
    state.set_user({
        "id": 1,
        "username": "admin",
        "first_name": "Demo",
        "last_name": "Admin",
        "occupation": "Admin",
    })

    window = MainWindow()
    window.btn_logout.click()
    qapp.processEvents()

    assert state.current_user is None
    assert window.current_user is None
    assert not window.isVisible()

    state.clear_user()
    window.deleteLater()


def test_logout_signal_does_not_bind_clicked_bool_to_confirm_callback():
    source = (Path(__file__).resolve().parents[1] / "ui" / "app" / "main_window.py").read_text(encoding="utf-8")
    assert "self.btn_logout.clicked.connect(self.on_logout)" not in source
    assert "self.btn_logout.clicked.connect(lambda _checked=False: self.on_logout())" in source


def test_action_tables_reserve_room_for_embedded_controls():
    root = Path(__file__).resolve().parents[1]
    table_source = (root / "ui" / "widgets" / "table_polish.py").read_text(encoding="utf-8")
    layout_source = (root / "ui" / "theme" / "layout.py").read_text(encoding="utf-8")

    assert "has_action_column" in table_source
    assert "LayoutMetrics.TABLE_ACTION_ROW_HEIGHT" in table_source
    assert "TABLE_ACTION_ROW_HEIGHT = 52" in layout_source
