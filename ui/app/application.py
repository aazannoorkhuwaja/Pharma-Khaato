"""Pharma-Khaato Qt application bootstrap."""

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


def _inventory_screen():
    from ui.screens.inventory_screen import InventoryScreen
    return InventoryScreen()


def _customer_screen():
    from ui.screens.customer_screen import CustomerScreen
    return CustomerScreen()


def _credit_screen():
    from ui.screens.khatoo_screen import KhatooScreen
    return KhatooScreen()


def _cash_screen():
    from ui.screens.cash_session_screen import CashSessionScreen
    return CashSessionScreen()


def _reports_screen():
    from ui.screens.reports_screen import ReportsScreen
    return ReportsScreen()


def _returns_screen():
    from ui.screens.returns_screen import ReturnsScreen
    return ReturnsScreen()


def _settings_screen():
    from ui.screens.settings_screen import SettingsScreen
    return SettingsScreen()


def run_app():
    app_controller = ApplicationController()
    app_controller.initialize()
    ThemeManager.load_preferences()

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

    try:
        needs_setup = app_controller.needs_first_run_setup()
    except Exception as exc:
        print(f"ERROR: Cannot verify employee registry (database issue): {exc}")
        return 1
    if needs_setup:
        wizard = FirstRunWizardDialog()
        if wizard.exec() != FirstRunWizardDialog.Accepted:
            print("First-run setup cancelled. Exiting application.")
            return 0

    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.Accepted or not SessionState.get_instance().current_user:
        print("Authentication cancelled or failed. Exiting application without accessing POS.")
        return 0

    current_user = SessionState.get_instance().current_user
    health = app_controller.health()
    window = MainWindow()

    # The POS is already populated by its constructor, so mark that initial
    # snapshot current. Secondary workflows are lazy-created only when needed.
    window.router.register_screen(
        "pos",
        POSScreen(),
        domains=("cash",),
        max_age_seconds=5.0,
        data_is_current=True,
    )
    window.router.register_screen_factory(
        "inventory",
        _inventory_screen,
        domains=("inventory",),
        max_age_seconds=30.0,
    )
    window.router.register_screen_factory(
        "customers",
        _customer_screen,
        domains=("customers", "credit"),
        max_age_seconds=30.0,
    )
    window.router.register_screen_factory(
        "khatoo",
        _credit_screen,
        domains=("credit", "customers"),
        max_age_seconds=20.0,
    )
    window.router.register_screen_factory(
        "cash_session",
        _cash_screen,
        domains=("cash", "sales", "credit", "returns"),
        max_age_seconds=10.0,
    )
    window.router.register_screen_factory(
        "reports",
        _reports_screen,
        domains=("reports", "sales", "inventory", "credit", "returns"),
        max_age_seconds=30.0,
    )
    window.router.register_screen_factory(
        "returns",
        _returns_screen,
        domains=("returns", "sales"),
        max_age_seconds=30.0,
    )
    window.router.register_screen_factory(
        "settings",
        _settings_screen,
        domains=("settings", "staff", "backups"),
        max_age_seconds=60.0,
    )

    if health["db_connected"]:
        window.status_bar.showMessage(f"Signed in: {current_user.get('username')} • Ready")
    else:
        window.status_bar.showMessage(f"Signed in: {current_user.get('username')} • System needs attention")

    # MainWindow already read the active user once during construction. Avoid a
    # second session/shift query here; just navigate to the ready counter.
    window.on_nav_clicked("pos")
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        area = screen.availableGeometry()
        window.resize(
            min(1440, max(900, int(area.width() * 0.94))),
            min(900, max(600, int(area.height() * 0.90))),
        )
    window.show()
    return app.exec()
