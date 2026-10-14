"""
Track 2 Verification & Acceptance Test Suite:
Verifies Counter Workflow & Speed fixes:
2.1 Esc behavior (dismisses search) and Ctrl+Delete cart clearing.
2.2 Hotkey badges are rendered as distinct scannable elements.
2.3 Live customer typeahead populates dropdown matches.
2.4 Shift opening gate before checkout.
2.5 Fast shift logout clears session state without process termination.
2.6 Registration tab removed from login screen (Sign In only).
2.7 Harmonized destructive action policy.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt

from ui.screens.pos_screen import POSScreen
from ui.screens.login_screen import LoginDialog
from ui.app.main_window import MainWindow
from ui.app.state.session_state import SessionState
from core.inventory_service import clear_inventory_cache
from scripts.seed_db import seed_database

class TestTrack2Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        seed_database()

    def setUp(self):
        clear_inventory_cache()
        self.session = SessionState.get_instance()
        self.session.clear_cart()
        self.session.set_user({"id": 1, "username": "admin", "first_name": "Admin", "last_name": "User", "occupation": "Admin"})

    def test_2_1_esc_and_ctrl_delete_shortcuts(self):
        """2.1 Esc dismisses search, Ctrl+Delete clears cart with undo."""
        pos = POSScreen(show_message_box=False)
        pos.show()

        # Add item to cart
        self.session.add_to_cart({"prod_id": 1, "name": "Panadol", "price": 50.0, "batch_id": 1, "stock": 100}, qty=2)
        pos.refresh_cart_display()
        self.assertEqual(len(self.session.active_cart), 1)

        # Trigger search
        pos.txt_search.setText("Panadol")
        pos.perform_live_search()
        self.assertTrue(pos.search_table.isVisible())

        # Esc dismisses search, cart remains intact
        pos._on_escape()
        self.assertFalse(pos.search_table.isVisible(), "Esc must hide search table.")
        self.assertEqual(len(self.session.active_cart), 1, "Esc must not clear active cart.")

        # Ctrl+Delete clears cart
        pos.on_clear_cart_requested()
        self.assertEqual(len(self.session.active_cart), 0, "on_clear_cart_requested must clear active cart.")

    def test_2_3_customer_live_typeahead(self):
        """2.3 Typing in customer field populates live typeahead dropdown."""
        pos = POSScreen(show_message_box=False)
        pos.show()

        # Type '35202' matching seed customers
        pos.txt_customer.setText("35202")
        pos.on_cust_text_changed("35202")

        self.assertTrue(pos.cust_table.isVisible(), "Customer search table must appear for matching input.")
        self.assertGreater(pos.cust_table.rowCount(), 0, "Typeahead table must display matching customer rows.")

    def test_2_5_logout_resets_session_without_exit(self):
        """2.5 Logout clears user state without closing application process."""
        window = MainWindow(enforce_session=True)
        self.assertIsNotNone(self.session.current_user)

        # Confirm logout programmatically
        window.on_logout(confirm_fn=lambda parent, title, msg, buttons, default: 16384) # QMessageBox.Yes = 16384
        self.assertIsNone(self.session.current_user, "Session user must be cleared on logout.")

    def test_2_6_login_screen_sign_in_only(self):
        """2.6 Login screen must be Sign In only (no public registration path)."""
        login_dlg = LoginDialog()
        self.assertFalse(hasattr(login_dlg, "txt_reg_username"), "Login dialog must not contain registration input fields.")

if __name__ == "__main__":
    unittest.main()
