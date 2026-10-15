"""
Track 5 Verification & Acceptance Test Suite:
Verifies Performance & Scalability fixes:
5.1 Lazy screen creation via router factory registration.
5.2 Batched customer debt query (search_customers_with_debt single SQL roundtrip).
5.3 Implementation of on_screen_show hooks across secondary screens.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from ui.app.router import AppRouter
from ui.screens.inventory_screen import InventoryScreen
from ui.screens.customer_screen import CustomerScreen
from ui.screens.khatoo_screen import KhatooScreen
from ui.screens.cash_session_screen import CashSessionScreen
from ui.screens.reports_screen import ReportsScreen
from core.customer_service import search_customers_with_debt
from scripts.seed_db import seed_database

class TestTrack5Performance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        seed_database()

    def test_5_1_lazy_router_factories(self):
        """5.1 Router instantiates screens lazily from registered factories on navigation."""
        router = AppRouter()
        created = {"count": 0}
        
        def factory():
            created["count"] += 1
            return CustomerScreen(show_message_box=False)

        router.register_screen_factory("customers", factory)
        self.assertEqual(created["count"], 0, "Factory must not be called upon registration.")
        
        ok = router.navigate_to("customers")
        self.assertTrue(ok)
        self.assertEqual(created["count"], 1, "Factory must be called exactly once on first navigation.")

    def test_5_2_batched_customer_debt_query(self):
        """5.2 search_customers_with_debt returns 6-tuple with debt pre-calculated."""
        results = search_customers_with_debt("")
        self.assertTrue(len(results) > 0)
        for item in results:
            self.assertEqual(len(item), 6, "Batched query result must return 6 elements (cnic, fname, lname, email, city, debt).")

    def test_5_3_on_screen_show_hooks(self):
        """5.3 All secondary screens implement on_screen_show hook."""
        for screen_cls in (InventoryScreen, CustomerScreen, KhatooScreen, CashSessionScreen, ReportsScreen):
            screen = screen_cls(show_message_box=False)
            self.assertTrue(hasattr(screen, "on_screen_show"), f"{screen_cls.__name__} must implement on_screen_show hook.")

if __name__ == "__main__":
    unittest.main()
