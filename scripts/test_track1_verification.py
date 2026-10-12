"""
Track 1 Verification & Acceptance Test Suite:
Verifies Money & Data Integrity fixes:
1.1 Duplicate checkout lock (rapid checkout calls yield exactly 1 sale record).
1.2 Unresolved CNIC credit sale blocking (credit checkout without a registered customer is rejected).
1.3 Inventory batch table full sellable FEFO dataset verification.
1.4 F6 Recall Sale dialog triggering when multiple sales are held.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt

from ui.screens.pos_screen import POSScreen, RecallSaleDialog
from ui.screens.inventory_screen import InventoryScreen
from ui.app.state.session_state import SessionState
from core.pos_service import get_sales_history
from core.inventory_service import clear_inventory_cache, get_all_active_batches, search_products
from core.hold_sale_service import hold_sale, get_held_sales
from scripts.seed_db import seed_database

class TestTrack1Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        seed_database()

    def setUp(self):
        clear_inventory_cache()
        self.session = SessionState.get_instance()
        self.session.clear_cart()
        self.session.set_user({"id": 1, "username": "admin", "first_name": "Admin", "last_name": "User"})

    def test_1_1_duplicate_checkout_lock(self):
        """1.1 Firing checkout twice in rapid succession creates exactly ONE sale record."""
        pos = POSScreen(show_message_box=False)
        pos.show()
        
        # Add product to cart
        prods = search_products("Panadol")
        self.assertTrue(len(prods) > 0, "Seed data must contain Panadol")
        p_id, p_name, p_price, b_id, b_qty, b_exp = prods[0]
        self.session.add_to_cart({"prod_id": p_id, "name": p_name, "price": float(p_price), "batch_id": b_id, "stock": b_qty}, qty=1)
        pos.refresh_cart_display()
        self.assertEqual(len(self.session.active_cart), 1)

        initial_sales = len(get_sales_history())

        # Simulate double checkout call
        pos.on_checkout()
        pos.on_checkout()  # Second call while cart cleared/flag handled

        updated_sales = len(get_sales_history())
        self.assertEqual(updated_sales, initial_sales + 1, "Exactly one sale must be created for a single cart checkout.")

    def test_1_2_block_unresolved_cnic_credit_sale(self):
        """1.2 Khatoo credit checkout with non-existent CNIC must be blocked."""
        pos = POSScreen(show_message_box=False)
        pos.show()
        
        # Add item to cart
        prods = search_products("Panadol")
        p_id, p_name, p_price, b_id, b_qty, b_exp = prods[0]
        self.session.add_to_cart({"prod_id": p_id, "name": p_name, "price": float(p_price), "batch_id": b_id, "stock": b_qty}, qty=1)
        pos.refresh_cart_display()

        # Set payment method to Khatoo Credit
        idx = pos.cmb_pay_method.findData("Khatoo Credit")
        pos.cmb_pay_method.setCurrentIndex(idx)

        # Enter fake/unregistered CNIC
        pos.txt_customer.setText("9999999999999")
        pos.on_customer_lookup()
        self.assertFalse(pos.is_customer_verified, "Unregistered CNIC must not be marked as verified.")

        initial_sales = len(get_sales_history())
        pos.on_checkout()
        updated_sales = len(get_sales_history())

        self.assertEqual(updated_sales, initial_sales, "Credit checkout with unverified customer MUST be blocked.")
        self.assertEqual(len(self.session.active_cart), 1, "Cart must remain intact when credit checkout is blocked.")

    def test_1_3_inventory_batches_full_dataset(self):
        """1.3 Inventory screen batches table must display ALL sellable FEFO batches, not just near-expiry."""
        inv = InventoryScreen(show_message_box=False)
        db_batches = get_all_active_batches()
        tbl_count = inv.tbl_batches.rowCount()
        self.assertEqual(tbl_count, len(db_batches), f"Batches table count ({tbl_count}) must match DB sellable batches count ({len(db_batches)}).")

    def test_1_4_f6_recall_picker_triggering(self):
        """1.4 F6 recall must trigger RecallSaleDialog when multiple sales are on hold."""
        # Hold 2 sales
        item1 = [{"prod_id": 1, "name": "Item 1", "price": 100.0, "qty": 1, "subtotal": 100.0, "batch_id": 1}]
        item2 = [{"prod_id": 2, "name": "Item 2", "price": 200.0, "qty": 2, "subtotal": 400.0, "batch_id": 2}]
        hold_sale("WALKIN", 1, item1, note="Hold 1")
        hold_sale("WALKIN", 1, item2, note="Hold 2")

        held = get_held_sales()
        self.assertGreaterEqual(len(held), 2, "At least 2 sales should be on hold.")

        dlg = RecallSaleDialog(held)
        self.assertEqual(dlg.table.rowCount(), len(held), "RecallSaleDialog table must show all held sales.")
        dlg.table.selectRow(1)
        dlg.on_confirm()
        self.assertIsNotNone(dlg.selected_hold_id)

if __name__ == "__main__":
    unittest.main()
