#!/usr/bin/env python3
"""Offscreen GUI smoke/screenshots using only the isolated demo database."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# This import sets PHARMA_KHAATO_DATA_DIR before any core/UI module resolves it.
from scripts.demo_mode import (
    DEMO_ADMIN_PASSWORD,
    DEMO_ADMIN_USER,
    reset_demo_storage,
    seed_demo_database,
)

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.theme.theme_manager import ThemeManager
from ui.app.main_window import MainWindow
from ui.app.state.session_state import SessionState
from ui.screens.login_screen import LoginDialog
from ui.screens.pos_screen import POSScreen
from ui.screens.inventory_screen import InventoryScreen
from ui.screens.customer_screen import CustomerScreen
from ui.screens.khatoo_screen import KhatooScreen
from ui.screens.cash_session_screen import CashSessionScreen
from ui.screens.reports_screen import ReportsScreen
from ui.screens.returns_screen import ReturnsScreen
from ui.screens.settings_screen import SettingsScreen


SCREENSHOTS_DIR = ROOT / "artifacts" / "gui_screenshots"


def _capture(app, widget, filename: str, wait_ms: int = 500):
    app.processEvents()
    QTest.qWait(wait_ms)
    app.processEvents()
    path = SCREENSHOTS_DIR / filename
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Could not save GUI smoke screenshot: {path}")


def run_gui_verification() -> int:
    print("=== Pharma-Khaato isolated GUI smoke verification ===")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    reset_demo_storage()
    seed_demo_database()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    ThemeManager.load_preferences()
    ThemeManager.apply_theme()

    login = LoginDialog()
    login.txt_username.setText(DEMO_ADMIN_USER)
    login.txt_password.setText(DEMO_ADMIN_PASSWORD)
    _capture(app, login, "01_login_screen.png", 100)
    login.handle_login()
    for _attempt in range(100):
        if not login._signing_in:
            break
        QTest.qWait(50)
        app.processEvents()
    if not SessionState.get_instance().current_user:
        raise RuntimeError("Demo administrator login failed in GUI smoke test")

    current_user = SessionState.get_instance().current_user
    window = MainWindow()
    if hasattr(window, "set_active_user"):
        window.set_active_user(current_user)

    screens = {
        "pos": POSScreen(show_message_box=False),
        "inventory": InventoryScreen(show_message_box=False),
        "customers": CustomerScreen(show_message_box=False),
        "khatoo": KhatooScreen(show_message_box=False),
        "cash_session": CashSessionScreen(show_message_box=False),
        "reports": ReportsScreen(show_message_box=False),
        "returns": ReturnsScreen(show_message_box=False),
        "settings": SettingsScreen(show_message_box=False),
    }
    domains = {
        "pos": ("cash",),
        "inventory": ("inventory",),
        "customers": ("customers", "credit"),
        "khatoo": ("credit", "customers"),
        "cash_session": ("cash", "sales", "credit", "returns"),
        "reports": ("reports", "sales", "inventory", "credit", "returns"),
        "returns": ("returns", "sales"),
        "settings": ("settings", "staff", "backups"),
    }
    for key, screen in screens.items():
        window.router.register_screen(key, screen, domains=domains[key])

    window.resize(1280, 800)
    window.show()
    QTest.qWait(200)

    sequence = [
        ("pos", "02_pos_screen.png"),
        ("inventory", "03_inventory_screen.png"),
        ("customers", "04_customers_screen.png"),
        ("khatoo", "05_customer_credit_screen.png"),
        ("cash_session", "06_cash_session_screen.png"),
        ("reports", "07_reports_screen.png"),
        ("returns", "08_returns_screen.png"),
        ("settings", "09_settings_screen.png"),
    ]
    for key, filename in sequence:
        print(f"[GUI] {key}")
        window.on_nav_clicked(key)
        _capture(app, window, filename)

    window.close()
    app.processEvents()
    print(f"PASS — GUI smoke screenshots saved to {SCREENSHOTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_gui_verification())
