"""Pharma-Khaato Qt application bootstrap."""

import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt, QLockFile, QTimer, QThreadPool

from config import ApplicationSettings
from controllers.application_controller import ApplicationController
from core.logger import get_logger
from ui.theme.theme_manager import ThemeManager
from ui.app.main_window import MainWindow
from ui.app.async_tasks import AsyncTaskRunner
from ui.app.state.session_state import SessionState
from ui.screens.first_run_wizard import FirstRunWizardDialog
from ui.screens.login_screen import LoginDialog
from ui.screens.pos_screen import POSScreen

logger = get_logger("PharmaKhaatoApplication")


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


def _acquire_single_instance(app: QApplication, app_controller: ApplicationController):
    """Prevent two interactive processes from opening the same local store.

    QLockFile handles stale locks after crashes. Headless CI/tests and explicitly
    isolated development runs may opt out because they use separate data dirs.
    The UI obtains the lock location through its application controller so the
    storage boundary remains outside the view layer.
    """
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return None
    if os.environ.get("PHARMA_KHAATO_ALLOW_MULTI_INSTANCE") == "1":
        return None

    lock = QLockFile(app_controller.single_instance_lock_path())
    lock.setStaleLockTime(30_000)
    if lock.tryLock(100):
        app.aboutToQuit.connect(lock.unlock)
        return lock

    QMessageBox.warning(
        None,
        f"{ApplicationSettings.DISPLAY_NAME} is already open",
        "Another copy of Pharma Khaato is already running for this workstation.\n\n"
        "Use the existing window, or close it before starting the application again. "
        "This protection keeps the local pharmacy database safe from competing desktop sessions.",
    )
    return False


def run_app():
    app_controller = ApplicationController()

    app = QApplication.instance()
    if not app:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)

    app.setApplicationName(ApplicationSettings.DISPLAY_NAME)
    app.setApplicationDisplayName(ApplicationSettings.DISPLAY_NAME)
    app.setApplicationVersion(ApplicationSettings.APP_VERSION)
    app.setOrganizationName(ApplicationSettings.ORGANIZATION)
    app.setOrganizationDomain(ApplicationSettings.APP_ID)
    app.aboutToQuit.connect(app_controller.shutdown)
    app.setStyle("Fusion")
    QThreadPool.globalInstance().setMaxThreadCount(app_controller.worker_thread_limit())

    instance_lock = _acquire_single_instance(app, app_controller)
    if instance_lock is False:
        app_controller.shutdown()
        return 0
    # Keep the lock object alive for the whole QApplication lifetime.
    app._pharma_khaato_instance_lock = instance_lock

    while True:
        try:
            app_controller.initialize()
            break
        except Exception as exc:
            if app_controller.is_remote():
                logger.warning("The shop counter cannot connect: %s", exc)
                reply = QMessageBox.warning(None, "Shop Connection Unavailable",
                    "This counter cannot reach the shop computer. Check that the shop computer and router are on, then retry. No local copy of the stock or customer balance will be used.",
                    QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Retry)
                if reply == QMessageBox.StandardButton.Retry:
                    continue
                return 1
            logger.exception("Database startup needs recovery: %s", exc)
            from ui.screens.recovery_screen import RecoveryDialog
            RecoveryDialog().exec()
            return 1

    ThemeManager.load_preferences()
    ThemeManager.apply_theme()

    try:
        needs_setup = app_controller.needs_first_run_setup()
    except Exception as exc:
        logger.exception("Cannot verify employee registry during startup: %s", exc)
        QMessageBox.critical(
            None,
            "Pharma Khaato could not start",
            "The local pharmacy database could not be opened. No sale was started.\n\n"
            "Run the launch self-check or contact support before continuing.",
        )
        return 1
    setup_username = ""
    if needs_setup:
        wizard = FirstRunWizardDialog()
        if wizard.exec() != FirstRunWizardDialog.Accepted:
            return 0
        setup_username = wizard.txt_user.text().strip()

    try:
        app._pharma_shop_server = app_controller.start_shop_service()
    except Exception as exc:
        logger.exception("The configured shop service could not start: %s", exc)
        QMessageBox.critical(None, "Shop Connection Unavailable", "The shop service could not start. Other counters cannot connect. Check Settings or contact support before continuing.")
        return 1

    login_dialog = LoginDialog()
    if setup_username and hasattr(login_dialog, "txt_username"):
        login_dialog.txt_username.setText(setup_username)
        login_dialog.txt_password.setFocus()
    if login_dialog.exec() != QDialog.Accepted or not SessionState.get_instance().current_user:
        return 0

    current_user = SessionState.get_instance().current_user
    window = MainWindow()

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

    # Show the counter before health/backup work. Slow disk/database checks must
    # never be on the cashier's login critical path.
    window.status_bar.showMessage(f"Signed in: {current_user.get('username')} • Ready")
    window.on_nav_clicked("pos")
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        area = screen.availableGeometry()
        window.resize(
            min(1440, max(900, int(area.width() * 0.94))),
            min(900, max(600, int(area.height() * 0.90))),
        )
    window.show()
    if needs_setup:
        QTimer.singleShot(0, window.show_getting_started)

    startup_tasks = AsyncTaskRunner(window)
    window._startup_tasks = startup_tasks

    window._health_issue = ""
    window._backup_issue = ""
    def show_runtime_status():
        issue = window._health_issue or window._backup_issue
        user = window.current_user or {}
        window.status_bar.showMessage(f"Signed in: {user.get('username', '')} • " + (issue or "Ready"))

    def apply_health(health):
        issues = health.get("issues") or []
        healthy = health.get("db_connected") and health.get("db_integrity_ok") and not issues
        window._health_issue = "" if healthy else (str(issues[0]) if issues else "System needs attention. Open Settings → System & Recovery.")
        show_runtime_status()

    startup_tasks.run(
        app_controller.health,
        apply_health,
        lambda _details: window.status_bar.showMessage(
            f"Signed in: {current_user.get('username')} • System check unavailable"
        ),
    )

    def backup_finished(result):
        window._backup_in_progress = False
        ok, detail = result
        if not ok:
            logger.warning("Automatic daily backup was not created: %s", detail)
            window._backup_issue = "Backup needs attention: " + str(detail)
        else:
            window._backup_issue = ""
        show_runtime_status()

    window._backup_in_progress = False
    def check_backup():
        if window._backup_in_progress:
            return
        window._backup_in_progress = True
        startup_tasks.run(
            lambda: app_controller.ensure_daily_backup(retention=14),
            backup_finished,
            lambda details: backup_finished((False, "The backup check failed. Open Settings → System & Recovery.")),
        )
    check_backup()
    window._backup_timer = QTimer(window)
    window._backup_timer.setInterval(60_000)
    window._backup_timer.timeout.connect(check_backup)
    window._backup_timer.start()
    window._health_timer = QTimer(window)
    window._health_timer.setInterval(300_000)
    window._health_timer.timeout.connect(lambda: startup_tasks.run(app_controller.health, apply_health))
    window._health_timer.start()

    return app.exec()
