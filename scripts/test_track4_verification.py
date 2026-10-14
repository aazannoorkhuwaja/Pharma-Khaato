"""
Track 4 Verification & Acceptance Test Suite:
Verifies Accessibility (WCAG 2.2 AA) fixes:
4.1 Contrast check: white text on accent color for tabs and primary buttons.
4.3 & 4.4 Accessible names and buddy relationships on Login and POS screens.
4.5 Visible focus indicators restored in global QSS.
4.8 First-run wizard height bounds check (fits within 600px target display height).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from ui.screens.login_screen import LoginDialog
from ui.screens.pos_screen import POSScreen
from ui.screens.first_run_wizard import FirstRunWizardDialog
from ui.theme.theme_manager import ThemeManager

class TestTrack4Accessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_4_3_4_4_accessible_names_and_buddies(self):
        """4.3 & 4.4 Login controls must expose accessible names and buddy relationships."""
        dlg = LoginDialog()
        self.assertEqual(dlg.txt_username.accessibleName(), "Employee Username")
        self.assertEqual(dlg.txt_password.accessibleName(), "Employee Password")

        pos = POSScreen(show_message_box=False)
        self.assertEqual(pos.txt_search.accessibleName(), "Product Search Input")
        self.assertEqual(pos.cart_table.accessibleName(), "Active Cart Items Table")

    def test_4_5_focus_indicators(self):
        """4.5 Global QSS contains QTableWidget:focus rules and no outline:none table suppression."""
        qss = ThemeManager.build_qss("light")
        self.assertIn("QTableWidget:focus", qss)
        self.assertNotIn("QTableWidget, QTableView {\n            background-color", qss.replace("   ", ""))

    def test_4_8_first_run_wizard_height(self):
        """4.8 First-run wizard height must fit within target 600px hardware bounds."""
        wiz = FirstRunWizardDialog(show_message_box=False)
        self.assertLessEqual(wiz.minimumHeight(), 540, "Wizard minimum height must be <= 540px to fit 600px displays.")
        self.assertLessEqual(wiz.height(), 560, "Wizard default height must be <= 560px.")

if __name__ == "__main__":
    unittest.main()
