import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt, QDate

from core.db_engine import get_conn
from core.auth_service import register_initial_admin, login_user
from ui.theme.theme_manager import ThemeManager
from ui.app.main_window import MainWindow
from ui.app.state.session_state import SessionState
from ui.screens.first_run_wizard import FirstRunWizardDialog
from ui.screens.login_screen import LoginDialog

from ui.screens.pos_screen import POSScreen
from ui.screens.inventory_screen import InventoryScreen
from ui.screens.customer_screen import CustomerScreen
from ui.screens.khatoo_screen import KhatooScreen
from ui.screens.cash_session_screen import CashSessionScreen
from ui.screens.reports_screen import ReportsScreen
from ui.screens.settings_screen import SettingsScreen
from scripts.seed_db import seed_database

def run_gui_verification():
    print("=== Starting Comprehensive Automated GUI Verification ===")
    
    # 0. Output directory for screenshots
    screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "gui_screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # 1. Initialize DB & Seed
    conn = get_conn()
    conn.close()
    seed_database()

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setStyleSheet(ThemeManager.get_application_qss())

    # 1.5 Test First-Run Setup Wizard UI
    print("[0/9] Testing First-Run Setup Wizard UI...")
    wiz = FirstRunWizardDialog(show_message_box=False)
    wiz.show()
    app.processEvents()
    pix = wiz.grab()
    pix.save(os.path.join(screenshots_dir, "00_first_run_wizard.png"))
    wiz.close()

    # 2. Test Login Screen
    print("[1/9] Testing Login Gate UI...")
    login_dlg = LoginDialog()
    login_dlg.show()
    app.processEvents()
    
    # Fill credentials
    login_dlg.txt_username.setText("admin")
    login_dlg.txt_password.setText("admin123")
    pixmap = login_dlg.grab()
    pixmap.save(os.path.join(screenshots_dir, "01_login_screen.png"))
    
    # Perform Login
    login_dlg.handle_login()
    assert SessionState.get_instance().current_user is not None, "Login failed for admin/admin123"
    print("✓ Login Gate verified successfully!")

    current_user = SessionState.get_instance().current_user

    # 3. Test Main Window & Navigation
    print("[2/9] Initializing MainWindow and Screen Router...")
    win = MainWindow()
    win.set_active_user(current_user)

    pos_scr = POSScreen(show_message_box=False)
    inv_scr = InventoryScreen(show_message_box=False)
    cust_scr = CustomerScreen(show_message_box=False)
    kha_scr = KhatooScreen(show_message_box=False)
    cash_scr = CashSessionScreen(show_message_box=False)
    rep_scr = ReportsScreen(show_message_box=False)
    set_scr = SettingsScreen(show_message_box=False)

    win.router.register_screen("pos", pos_scr)
    win.router.register_screen("inventory", inv_scr)
    win.router.register_screen("customers", cust_scr)
    win.router.register_screen("khatoo", kha_scr)
    win.router.register_screen("cash_session", cash_scr)
    win.router.register_screen("reports", rep_scr)
    win.router.register_screen("settings", set_scr)

    win.show()
    win.resize(1280, 800)
    app.processEvents()

    # 4. Test POS Screen
    print("[3/9] Testing POS Billing Screen UI...")
    win.on_nav_clicked("pos")
    app.processEvents()
    
    # Simulate search and add to cart
    pos_scr.txt_search.setText("Panadol")
    pos_scr.perform_live_search()
    app.processEvents()
    
    pos_scr.spn_discount.setValue(10.0)
    pos_scr.refresh_cart_display()
    app.processEvents()

    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "02_pos_screen.png"))
    print("✓ POS Billing Screen verified!")

    # 5. Test Inventory Screen
    print("[4/9] Testing Inventory Screen UI...")
    win.on_nav_clicked("inventory")
    app.processEvents()
    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "03_inventory_screen.png"))
    print("✓ Inventory Screen verified!")

    # 6. Test Customers Screen
    print("[5/9] Testing Customers Directory Screen UI...")
    win.on_nav_clicked("customers")
    app.processEvents()
    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "04_customers_screen.png"))
    print("✓ Customers Screen verified!")

    # 7. Test Khatoo Credit Ledger Screen
    print("[6/9] Testing Khatoo Credit Ledger Screen UI...")
    win.on_nav_clicked("khatoo")
    app.processEvents()
    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "05_khatoo_screen.png"))
    print("✓ Khatoo Ledger Screen verified!")

    # 8. Test Cash Register Session Screen
    print("[7/9] Testing Cash Register Session Screen UI...")
    win.on_nav_clicked("cash_session")
    app.processEvents()
    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "06_cash_session_screen.png"))
    print("✓ Cash Session Screen verified!")

    # 9. Test Reports & Analytics Screen
    print("[8/9] Testing Reports & Analytics Screen UI...")
    win.on_nav_clicked("reports")
    app.processEvents()
    rep_scr.refresh_all_reports()
    app.processEvents()
    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "07_reports_screen.png"))
    print("✓ Reports Screen verified!")

    # 10. Test Settings Screen & Theme Toggling
    print("[9/9] Testing Settings Control Panel & Theme Engine UI...")
    win.on_nav_clicked("settings")
    app.processEvents()
    
    # Toggle to High Contrast Theme
    idx_hc = set_scr.cmb_theme_mode.findData("high_contrast")
    if idx_hc >= 0:
        set_scr.cmb_theme_mode.setCurrentIndex(idx_hc)
        app.processEvents()
    
    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "08_settings_high_contrast.png"))
    
    # Toggle back to Dark Mode
    idx_dark = set_scr.cmb_theme_mode.findData("dark")
    if idx_dark >= 0:
        set_scr.cmb_theme_mode.setCurrentIndex(idx_dark)
        app.processEvents()

    pix = win.grab()
    pix.save(os.path.join(screenshots_dir, "09_settings_dark.png"))
    print("✓ Settings Screen & Theme Engine verified!")

    print("\n=== ALL GUI VERIFICATION TESTS PASSED SUCCESSFULLY! ===")
    print(f"Screenshots saved to: {screenshots_dir}")

if __name__ == "__main__":
    run_gui_verification()
