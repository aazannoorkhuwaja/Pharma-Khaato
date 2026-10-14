"""Pharma-Khaato responsive desktop application shell."""

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QFrame, QStatusBar, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from config import ApplicationSettings
from ui.app.router import AppRouter
from ui.theme.tokens import ThemeTokens
from ui.theme.theme_manager import ThemeManager
from ui.theme.layout import LayoutMetrics
from ui.app.state.session_state import SessionState
from ui.ux_copy import NAV_ITEMS, NAV_BY_KEY, role_label
from controllers.cash_session_controller import CashSessionController

_CASH_CONTROLLER = CashSessionController()


def _qt_button_text(text: str) -> str:
    return str(text).replace("&", "&&")


class MainWindow(QMainWindow):
    """Primary shell with adaptive navigation for 900px through 4K desktops."""

    def __init__(self, parent=None, enforce_session: bool = True):
        super().__init__(parent)
        if enforce_session and not SessionState.get_instance().current_user:
            raise PermissionError(
                "Access Denied: Unauthenticated attempt to instantiate MainWindow without an active login session."
            )

        self.setWindowTitle(f"{ApplicationSettings.DISPLAY_NAME} — Pharmacy POS")
        self.resize(1366, 768)
        self.setMinimumSize(LayoutMetrics.SHELL_MIN_WIDTH, LayoutMetrics.SHELL_MIN_HEIGHT)
        self.current_user = SessionState.get_instance().current_user
        self._sidebar_mode = None

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebarFrame")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(8)

        self.brand_label = QLabel("PHARMA KHAATO")
        self.brand_label.setObjectName("h2")
        self.brand_label.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 800;")
        self.sub_brand = QLabel(ApplicationSettings.PRODUCT_TAGLINE)
        self.sub_brand.setObjectName("caption")
        self.sub_brand.setWordWrap(True)
        sidebar_layout.addWidget(self.brand_label)
        sidebar_layout.addWidget(self.sub_brand)

        self.lbl_clock = QLabel()
        self.lbl_clock.setObjectName("caption")
        self.lbl_clock.setStyleSheet("font-weight: 600;")
        sidebar_layout.addWidget(self.lbl_clock)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        sidebar_layout.addSpacing(8)

        self.nav_buttons = {}
        self.shortcuts = {}
        self._nav_items = [(item.key, item.label, item.compact_label, item.shortcut) for item in NAV_ITEMS]
        for key, text, short_text, shortcut_key in self._nav_items:
            btn = QPushButton()
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"{text} ({shortcut_key}) — {NAV_BY_KEY[key].help_text}")
            btn.setAccessibleName(text)
            btn.clicked.connect(lambda checked=False, k=key: self.on_nav_clicked(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

            shortcut = QShortcut(QKeySequence(shortcut_key), self)
            shortcut.activated.connect(lambda k=key: self.on_nav_clicked(k))
            self.shortcuts[key] = shortcut

        sidebar_layout.addStretch()
        self.user_badge = QLabel("User: Signed Out")
        self.user_badge.setObjectName("caption")
        self.user_badge.setWordWrap(True)
        self.user_badge.setStyleSheet("font-weight: 700;")
        sidebar_layout.addWidget(self.user_badge)

        self.lbl_version = QLabel(f"Version {ApplicationSettings.APP_VERSION}")
        self.lbl_version.setObjectName("caption")
        self.lbl_version.setToolTip("Installed Pharma Khaato version")
        sidebar_layout.addWidget(self.lbl_version)

        self.btn_about = QPushButton("About Pharma Khaato")
        self.btn_about.setObjectName("sidebarUtilityButton")
        self.btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_about.clicked.connect(self.show_about)
        sidebar_layout.addWidget(self.btn_about)

        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setObjectName("sidebarUtilityButton")
        self.btn_theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_toggle.clicked.connect(self.on_toggle_theme)
        sidebar_layout.addWidget(self.btn_theme_toggle)

        self.btn_logout = QPushButton("Sign Out")
        self.btn_logout.setObjectName("sidebarLogoutButton")
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        # QPushButton.clicked emits a checked(bool) argument. Do not wire it
        # directly to on_logout(confirm_fn=None), otherwise that bool is bound
        # to confirm_fn and later called as a function.
        self.btn_logout.clicked.connect(lambda _checked=False: self.on_logout())
        sidebar_layout.addWidget(self.btn_logout)

        self.router = AppRouter()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.router, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_shift_status = QLabel("Shift: Offline")
        self.lbl_shift_status.setStyleSheet(f"color: {ThemeTokens.WARNING}; font-weight: 700; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_shift_status)
        self.hint_label = QLabel()
        self.hint_label.setObjectName("caption")
        self.hint_label.setVisible(False)
        self.status_bar.addPermanentWidget(self.hint_label)

        if self.current_user:
            self.set_active_user(self.current_user)
        else:
            self.status_bar.showMessage("Ready")
        self._apply_sidebar_density(self.width(), force=True)
        self.update_clock()

    def resizeEvent(self, event):
        self._apply_sidebar_density(event.size().width())
        super().resizeEvent(event)

    def _apply_sidebar_density(self, width: int, force: bool = False):
        if width >= LayoutMetrics.SIDEBAR_FULL_AT:
            mode, sidebar_width = "full", LayoutMetrics.SIDEBAR_FULL
        elif width >= LayoutMetrics.SIDEBAR_COMPACT_AT:
            mode, sidebar_width = "compact", LayoutMetrics.SIDEBAR_COMPACT
        else:
            mode, sidebar_width = "mini", LayoutMetrics.SIDEBAR_MINI
        if not force and mode == self._sidebar_mode:
            return
        self._sidebar_mode = mode
        self.sidebar.setFixedWidth(sidebar_width)
        for key, text, short_text, shortcut_key in self._nav_items:
            self.nav_buttons[key].setText(_qt_button_text(text if mode != "mini" else short_text))
        self.brand_label.setText("PHARMA KHAATO" if mode != "mini" else "PK")
        self.sub_brand.setVisible(mode == "full")
        self.user_badge.setVisible(mode != "mini")
        self.lbl_version.setVisible(mode != "mini")
        self.btn_about.setText("About" if mode == "mini" else "About Pharma Khaato")
        if mode == "mini":
            self.btn_theme_toggle.setText("Theme")
            self.btn_logout.setText("Sign Out")
        else:
            self.refresh_theme_toggle_label(update_density=False)
            self.btn_logout.setText("Sign Out")
        self.update_clock()

    def update_clock(self):
        now = datetime.now()
        if self._sidebar_mode == "mini":
            self.lbl_clock.setText(now.strftime("%H:%M"))
            self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elif self._sidebar_mode == "compact":
            self.lbl_clock.setText(now.strftime("%a %d %b  %H:%M"))
            self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignLeft)
        else:
            self.lbl_clock.setText(now.strftime("%a, %b %d • %I:%M %p"))
            self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def on_nav_clicked(self, screen_key: str):
        allowed = self.get_allowed_screens()
        if screen_key not in allowed:
            item = NAV_BY_KEY.get(screen_key)
            label = item.label if item else screen_key
            self.status_bar.showMessage(f"You do not have permission to open {label}. Ask an administrator if you need access.")
            return
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == screen_key)
        self.router.navigate_to(screen_key)

    def get_allowed_screens(self):
        base = ["pos", "customers", "khatoo", "cash_session"]
        if not self.current_user or not isinstance(self.current_user, dict):
            return base + ["inventory", "reports", "returns", "settings"]
        role = str(self.current_user.get("occupation", "Admin")).lower()
        if "admin" in role or "manager" in role:
            return base + ["inventory", "reports", "returns", "settings"]
        if "pharm" in role:
            return base + ["inventory", "reports", "returns"]
        return base

    def show_about(self):
        support_line = (
            f"Support: {ApplicationSettings.SUPPORT_EMAIL}"
            if ApplicationSettings.SUPPORT_EMAIL
            else "Support: contact your system administrator or deployment partner"
        )
        QMessageBox.about(
            self,
            f"About {ApplicationSettings.DISPLAY_NAME}",
            f"<b>{ApplicationSettings.DISPLAY_NAME}</b><br>"
            f"{ApplicationSettings.PRODUCT_TAGLINE}<br><br>"
            f"Version {ApplicationSettings.APP_VERSION}<br>"
            f"{ApplicationSettings.PRODUCT_DESCRIPTION}<br><br>"
            f"{ApplicationSettings.DATA_NOTICE}<br><br>"
            f"{support_line}",
        )

    def on_toggle_theme(self):
        ThemeManager.toggle_theme(save=True)
        self.refresh_theme_toggle_label()

    def refresh_theme_toggle_label(self, update_density: bool = True):
        mode = ThemeManager.get_theme_mode()
        if self._sidebar_mode == "mini":
            self.btn_theme_toggle.setText("Theme")
        else:
            self.btn_theme_toggle.setText("Use Light Mode" if mode == "dark" else "Use Dark Mode")
        if update_density:
            self._apply_sidebar_density(self.width(), force=True)

    def set_active_user(self, user_dict):
        self.current_user = user_dict
        uname = user_dict.get("username", "Cashier") if isinstance(user_dict, dict) else str(user_dict)
        role = role_label(user_dict.get("occupation", "Staff")) if isinstance(user_dict, dict) else "Staff"
        emp_id = user_dict.get("id", 1) if isinstance(user_dict, dict) else 1
        self.user_badge.setText(f"{uname}\n{role}")
        try:
            active_sess = _CASH_CONTROLLER.active_session(emp_id)
            if active_sess:
                self.lbl_shift_status.setText("Shift Open")
                self.lbl_shift_status.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-weight: 700; padding: 0 8px;")
            else:
                self.lbl_shift_status.setText("Shift Closed")
                self.lbl_shift_status.setStyleSheet(f"color: {ThemeTokens.WARNING}; font-weight: 700; padding: 0 8px;")
        except Exception:
            self.lbl_shift_status.setText("Ready")
            self.lbl_shift_status.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-weight: 700; padding: 0 8px;")
        allowed = self.get_allowed_screens()
        for key, btn in self.nav_buttons.items():
            btn.setVisible(key in allowed)
        if "pos" in allowed:
            self.on_nav_clicked("pos")
        self.status_bar.showMessage(f"Signed in: {uname} • Ready")

    def on_logout(self, confirm_fn=None):
        uname = self.current_user.get("username", "") if isinstance(self.current_user, dict) else ""
        cart = SessionState.get_instance().active_cart
        cart_warning = (
            f"\n\nWarning: there are {len(cart)} unsaved item(s) in the active cart. They will be lost unless you hold the sale first."
            if cart else ""
        )
        name_part = f" for {uname}" if uname else ""
        if confirm_fn is not None:
            reply = confirm_fn(
                self, "Sign Out", f"Sign out{name_part}?{cart_warning}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
        elif os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            reply = QMessageBox.StandardButton.Yes
        else:
            reply = QMessageBox.question(
                self, "Sign Out", f"Sign out{name_part}?{cart_warning}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
        if reply != QMessageBox.StandardButton.Yes:
            return
        SessionState.get_instance().clear_user()
        self.current_user = None
        self.user_badge.setText("User: Signed Out")
        self.status_bar.showMessage("Signed Out")
        self.hide()
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            from ui.screens.login_screen import LoginDialog
            login_dlg = LoginDialog()
            if login_dlg.exec() == QDialog.DialogCode.Accepted and SessionState.get_instance().current_user:
                self.set_active_user(SessionState.get_instance().current_user)
                self.show()
            else:
                self.close()
        else:
            self.close()
