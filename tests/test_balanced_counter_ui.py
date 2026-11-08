"""Native Qt and source regression checks for the Balanced Counter UI pilot.

Financial services are not mocked. CI still runs the existing checkout,
supplier, credit, recovery and LAN test suites independently.
"""
from pathlib import Path

from tests.test_recording_review import owner, settle  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]


def test_theme_has_navy_sidebar_and_keyboard_safe_payment_buttons():
    theme = (ROOT / "ui/theme/theme_manager.py").read_text(encoding="utf-8")
    pos = (ROOT / "ui/screens/pos_screen.py").read_text(encoding="utf-8")
    assert 'sidebar_bg = "#14243D"' in theme
    assert "QLabel#workspaceTitle" in theme
    assert "QPushButton#paymentOption:checked" in theme
    assert "def _select_payment_method(self, index)" in pos
    assert "self.session.pending_checkout or self._checkout_in_progress" in pos
    assert "*self.payment_choice_buttons" in pos


def test_tender_tiles_follow_combo_and_lock_during_pending_checkout(owner, qtbot):
    from ui.screens.pos_screen import POSScreen

    screen = POSScreen(show_message_box=False)
    qtbot.addWidget(screen)
    screen.resize(1130, 710)
    screen.show()
    settle(qtbot, screen)

    assert len(screen.payment_choice_buttons) == screen.cmb_pay_method.count() == 5
    assert screen.payment_choice_buttons[0].isChecked()

    screen._select_payment_method(2)
    assert screen.cmb_pay_method.currentData() == "Easypaisa"
    assert screen.payment_choice_buttons[2].isChecked()
    assert sum(b.isChecked() for b in screen.payment_choice_buttons) == 1

    screen._set_checkout_locked(True)
    assert all(not b.isEnabled() for b in screen.payment_choice_buttons)
    screen.session.pending_checkout = {"request": {"checkout_token": "pending-test"}}
    try:
        screen._select_payment_method(1)
        assert screen.cmb_pay_method.currentData() == "Easypaisa"
    finally:
        screen.session.pending_checkout = None
        screen._set_checkout_locked(False)
    settle(qtbot, screen)


def test_compact_density_reduces_spacing_without_shrinking_fonts():
    from ui.theme.theme_manager import ThemeManager

    original = ThemeManager.get_density()
    try:
        ThemeManager.set_density("standard", save=False)
        standard = ThemeManager.build_qss("light", 1.0)
        ThemeManager.set_density("compact", save=False)
        compact = ThemeManager.build_qss("light", 1.0)
        assert ThemeManager.get_density() == "compact"
        assert "min-height: 38px;" in standard
        assert "min-height: 34px;" in compact
        assert "font-size: 13px;" in standard
        assert "font-size: 13px;" in compact
        assert standard != compact
    finally:
        ThemeManager.set_density(original, save=False)


def test_owner_overview_only_routes_through_window_permissions():
    source = (ROOT / "ui/screens/reports_screen.py").read_text(encoding="utf-8")
    assert "Owner Overview & Reports" in source
    assert '"Review Stock Alerts", "inventory"' in source
    assert '"System & Backup", "settings"' in source
    assert "key not in window.get_allowed_screens()" in source
    assert "window.on_nav_clicked(key)" in source
