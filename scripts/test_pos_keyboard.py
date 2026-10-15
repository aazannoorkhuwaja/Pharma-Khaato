#!/usr/bin/env python3
"""Keyboard-only counter acceptance test against the isolated demo database."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from scripts.demo_mode import (
    DEMO_ADMIN_PASSWORD,
    DEMO_ADMIN_USER,
    reset_demo_storage,
    seed_demo_database,
)

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.db_engine import get_db
from ui.app.state.session_state import SessionState
from ui.screens.login_screen import LoginDialog
from ui.screens.pos_screen import POSScreen


PANADOL_BARCODE = "8961001000001"


def _purchase_count() -> int:
    with get_db() as (_conn, cur):
        cur.execute("SELECT COUNT(*) FROM Purchase")
        return int((cur.fetchone() or [0])[0] or 0)


def _last_purchase_tender() -> str:
    with get_db() as (_conn, cur):
        cur.execute("SELECT payment_method FROM Purchase ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return str(row[0]) if row else ""


def run_keyboard_acceptance() -> int:
    print("=== Pharma-Khaato keyboard-only counter acceptance ===")
    reset_demo_storage()
    seed_demo_database()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    state = SessionState.get_instance()
    state.clear_user()
    state.clear_cart()

    # Sign in without invoking the button with a mouse/pointer action.
    login = LoginDialog()
    login.show()
    login.activateWindow()
    login.txt_username.setFocus()
    QTest.keyClicks(login.txt_username, DEMO_ADMIN_USER)
    QTest.keyClick(login.txt_username, Qt.Key_Tab)
    if not login.txt_password.hasFocus():
        login.txt_password.setFocus()
    QTest.keyClicks(login.txt_password, DEMO_ADMIN_PASSWORD)
    QTest.keyClick(login.txt_password, Qt.Key_Return)
    app.processEvents()
    if not state.current_user:
        raise RuntimeError("Keyboard sign-in did not establish an authenticated session")

    screen = POSScreen(show_message_box=False)
    screen.resize(1280, 800)
    screen.show()
    screen.activateWindow()
    screen.setFocus()
    QTest.qWait(100)
    app.processEvents()

    # F1 must put the operator directly in product search.
    QTest.keyClick(screen, Qt.Key_F1)
    app.processEvents()
    if not screen.txt_search.hasFocus():
        raise RuntimeError("F1 did not focus product search")

    # Barcode + Enter must add the item without pointer interaction.
    QTest.keyClicks(screen.txt_search, PANADOL_BARCODE)
    QTest.keyClick(screen.txt_search, Qt.Key_Return)
    app.processEvents()
    if len(state.active_cart) != 1 or state.active_cart[0].get("name") != "Panadol 500mg":
        raise RuntimeError("Barcode + Enter did not add Panadol to the sale")

    # F5/F6 must preserve the sale through the hold/resume workflow.
    QTest.keyClick(screen, Qt.Key_F5)
    app.processEvents()
    if state.active_cart:
        raise RuntimeError("F5 did not hold and clear the active sale")
    QTest.keyClick(screen, Qt.Key_F6)
    app.processEvents()
    if len(state.active_cart) != 1 or state.active_cart[0].get("name") != "Panadol 500mg":
        raise RuntimeError("F6 did not resume the held sale")

    # Focus/action shortcuts used at the counter must remain keyboard reachable.
    QTest.keyClick(screen, Qt.Key_F2)
    app.processEvents()
    if not screen.txt_customer.hasFocus():
        raise RuntimeError("F2 did not focus customer search")

    payment_before = screen.cmb_pay_method.currentIndex()
    screen.setFocus()
    QTest.keyClick(screen, Qt.Key_F4)
    app.processEvents()
    if screen.cmb_pay_method.currentIndex() == payment_before:
        raise RuntimeError("F4 did not advance the payment method")
    # Return to Cash so the final assertion has a deterministic tender.
    while (screen.cmb_pay_method.currentData() or screen.cmb_pay_method.currentText()) != "Cash":
        QTest.keyClick(screen, Qt.Key_F4)
        app.processEvents()

    purchases_before = _purchase_count()
    screen.setFocus()
    QTest.keyClick(screen, Qt.Key_F10)
    app.processEvents()

    if state.active_cart:
        raise RuntimeError("F10 checkout succeeded but the sale cart did not clear")
    if _purchase_count() != purchases_before + 1:
        raise RuntimeError("F10 did not commit exactly one sale")
    if _last_purchase_tender() != "Cash":
        raise RuntimeError("Keyboard checkout persisted an unexpected payment tender")
    if not screen.txt_search.hasFocus():
        raise RuntimeError("Completed sale did not return focus to product search")

    screen.close()
    login.close()
    app.processEvents()
    print("PASS — keyboard-only sign-in/search/hold/resume/payment/checkout flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_keyboard_acceptance())
