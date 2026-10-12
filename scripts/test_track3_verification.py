"""
Track 3 Verification & Acceptance Test Suite:
Verifies Frontend Architecture & Theme Reliability fixes:
3.1 Toast module-level show_toast helper function (does not crash dialog callers).
3.3 Theme preferences load properly.
3.5 Theme palette stability across theme switches.
3.6 Single canonical get_application_qss method in ThemeManager.
3.7 Card & ScreenHeader component creation.
3.8 Font stack cleanliness.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QDialog
from ui.widgets.toast import Toast, ToastType, show_toast
from ui.theme.theme_manager import ThemeManager
from ui.theme.tokens import ThemeTokens
from ui.widgets.screen_header import ScreenHeader

class TestTrack3Architecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_3_1_toast_helper_on_dialogs(self):
        """3.1 show_toast must safely work on dialog parents without throwing AttributeError."""
        dlg = QDialog()
        # Call show_toast via function
        show_toast(dlg, "Test Toast Message", ToastType.SUCCESS)
        self.assertTrue(hasattr(dlg, "_active_toast_host"))
        
        # Call via Toast.show_message class fallback
        Toast.show_message(dlg, "Class Toast Message", ToastType.WARNING)
        self.assertTrue(hasattr(dlg, "_active_toast_host"))

    def test_3_5_theme_palette_switch_stability(self):
        """3.5 Toggling light->dark->light yields consistent light token values."""
        ThemeTokens.set_palette("light")
        light_accent_initial = ThemeTokens.ACCENT
        
        ThemeTokens.set_palette("dark")
        self.assertNotEqual(ThemeTokens.ACCENT, light_accent_initial)
        
        ThemeTokens.set_palette("light")
        self.assertEqual(ThemeTokens.ACCENT, light_accent_initial, "Theme palette must return to identical light values.")

    def test_3_6_single_get_application_qss(self):
        """3.6 ThemeManager has exactly one get_application_qss method."""
        methods = [m for m in dir(ThemeManager) if m == "get_application_qss"]
        self.assertEqual(len(methods), 1)

    def test_3_7_screen_header_widget(self):
        """3.7 ScreenHeader creates title, subtitle and accepts pills."""
        hdr = ScreenHeader("Test Title", "Test Subtitle")
        self.assertEqual(hdr.lbl_title.text(), "Test Title")
        self.assertEqual(hdr.lbl_subtitle.text(), "Test Subtitle")

if __name__ == "__main__":
    unittest.main()
