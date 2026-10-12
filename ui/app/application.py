"""
Pharma-Khaato Qt Application Bootstrap
Initializes database connection, QApplication, SessionState, First-Run Wizard, Login Gate, Theme, and launches MainWindow.
"""

import os
import sys
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt

from config import ApplicationSettings

from controllers.application_controller import ApplicationController
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

def run_app():
    app_controller = ApplicationController()

    # 1. Initialize database engine & migrations through the MVC controller.
    app_controller.initialize()

    # 2. Load Saved Theme Preferences & Font Scale
    ThemeManager.load_preferences()

    # 3. Qt Application Instance. Qt 6 is DPI-aware by default; PassThrough
    # preserves fractional Windows scaling (125/150%) instead of rounding it.
    app = QApplication.instance()
    if not app:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)

    app.setApplicationName(ApplicationSettings.APP_NAME)
    app.setApplicationVersion(ApplicationSettings.APP_VERSION)
    app.setOrganizationName("Pharma-Khaato")
    app.aboutToQuit.connect(app_controller.shutdown)
    app.setStyle("Fusion")
    ThemeManager.apply_theme()

    # 3. Check First-Run Setup Requirement
    try:
        needs_setup = app_controller.needs_first_run_setup()
    except Exception as e:
        # Database offline is NOT the same as a fresh install — never show
        # the admin wizard against an unreadable database.
        print(f"ERROR: Cannot verify employee registry (database issue): {e}")
        return 1
    if needs_setup:
        wizard = FirstRunWizardDialog()
        res = wizard.exec()
        if res != FirstRunWizardDialog.Accepted:
            print("First-run setup cancelled. Exiting application.")
            return 0

    # 4. Enforce Mandatory Login Gate
    login_dialog = LoginDialog()
    res = login_dialog.exec()
    if res != QDialog.Accepted or not SessionState.get_instance().current_user:
        print("Authentication cancelled or failed. Exiting application without accessing POS.")
        return 0

    current_user = SessionState.get_instance().current_user

    # 5. System Health Diagnostics
    health = app_controller.health()

    # 6. Launch Main Window for Authenticated Session
    window = MainWindow()
    window.set_active_user(current_user)

    # Register POS eagerly, and secondary management screens via lazy factories
    window.router.register_screen("pos", POSScreen())
    window.router.register_screen_factory("inventory", lambda: InventoryScreen())
    window.router.register_screen_factory("customers", lambda: CustomerScreen())
    window.router.register_screen_factory("khatoo", lambda: KhatooScreen())
    window.router.register_screen_factory("cash_session", lambda: CashSessionScreen())
    window.router.register_screen_factory("reports", lambda: ReportsScreen())
    window.router.register_screen_factory("settings", lambda: SettingsScreen())

    if health["db_connected"]:
        window.status_bar.showMessage(f"Signed in: {current_user.get('username')} • Ready")
    else:
        window.status_bar.showMessage(f"Signed in: {current_user.get('username')} • System needs attention")

    window.on_nav_clicked("pos")

    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        area = screen.availableGeometry()
        target_w = min(1440, max(900, int(area.width() * 0.94)))
        target_h = min(900, max(600, int(area.height() * 0.90)))
        window.resize(target_w, target_h)
    window.show()

    return app.exec()
