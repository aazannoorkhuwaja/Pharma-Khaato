"""
Pharma-Khaato Native Login & Registration Portal (PySide6)
Modal authentication gate providing options to Sign In or Register a new account at startup.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QTabWidget, QWidget, QComboBox
)
from PySide6.QtCore import Qt

from controllers.auth_controller import AuthController

_AUTH_CONTROLLER = AuthController()
from ui.theme.tokens import ThemeTokens
from ui.app.state.session_state import SessionState
from ui.widgets.responsive import configure_dialog

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pharma-Khaato — Sign In")
        configure_dialog(self, 520, 620, minimum_width=400, minimum_height=500)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.user_data = None

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeTokens.SURFACE_BASE};
                color: {ThemeTokens.TEXT_PRIMARY};
                font-family: {ThemeTokens.FONT_FAMILY};
            }}
            QFrame#card {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_MD}px;
            }}
            QTabWidget::pane {{
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {ThemeTokens.SURFACE_BASE};
                color: {ThemeTokens.TEXT_SECONDARY};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                padding: 8px 20px;
                font-weight: 600;
                border-top-left-radius: {ThemeTokens.RADIUS_SM}px;
                border-top-right-radius: {ThemeTokens.RADIUS_SM}px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                color: {ThemeTokens.ACCENT};
                border-bottom: 2px solid {ThemeTokens.ACCENT};
                font-weight: 700;
            }}
            QLineEdit, QComboBox {{
                background-color: {ThemeTokens.SURFACE_BASE};
                color: {ThemeTokens.TEXT_PRIMARY};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                padding: 4px 12px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {ThemeTokens.BORDER_FOCUS};
            }}
            QPushButton.primaryBtn {{
                background-color: {ThemeTokens.ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: {ThemeTokens.RADIUS_SM}px;
                padding: 8px 16px;
                font-weight: 700;
            }}
            QPushButton.primaryBtn:hover {{
                background-color: {ThemeTokens.ACCENT_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # Header
        title = QLabel("PHARMA-KHAATO")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 800; letter-spacing: 1px;")

        subtitle = QLabel("Sign in to continue")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-weight: 500;")

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)

        # Single Clean Sign In Form
        login_container = QWidget()
        login_layout = QVBoxLayout(login_container)
        login_layout.setContentsMargins(16, 16, 16, 16)
        login_layout.setSpacing(10)

        lbl_user = QLabel("Username")
        lbl_user.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-weight: 600;")
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Enter username")
        self.txt_username.setAccessibleName("Employee Username")
        lbl_user.setBuddy(self.txt_username)

        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-weight: 600;")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Enter password")
        self.txt_password.setAccessibleName("Employee Password")
        self.txt_password.returnPressed.connect(self.handle_login)
        lbl_pass.setBuddy(self.txt_password)

        login_layout.addWidget(lbl_user)
        login_layout.addWidget(self.txt_username)
        login_layout.addWidget(lbl_pass)
        login_layout.addWidget(self.txt_password)

        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setStyleSheet(f"color: {ThemeTokens.DANGER}; font-weight: 600;")
        login_layout.addWidget(self.lbl_error)

        btn_submit = QPushButton("Sign In")
        btn_submit.setObjectName("primaryButton")
        btn_submit.setCursor(Qt.PointingHandCursor)
        btn_submit.clicked.connect(self.handle_login)
        login_layout.addWidget(btn_submit)
        login_layout.addStretch()

        card_layout.addWidget(login_container)
        layout.addWidget(card)

    def handle_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        if not username or not password:
            self.lbl_error.setText("Enter your username and password.")
            return

        try:
            res = _AUTH_CONTROLLER.login(username, password)
            if res:
                emp_id, fname, lname, occupation = res
                self.user_data = {
                    "emp_id": emp_id,
                    "id": emp_id,
                    "username": username,
                    "first_name": fname,
                    "last_name": lname,
                    "occupation": occupation
                }
                SessionState.get_instance().set_user(self.user_data)
                self.accept()
            else:
                self.lbl_error.setText("Username or password is incorrect.")
                self.txt_password.clear()
                self.txt_password.setFocus()
        except PermissionError as pe:
            # Surface brute-force lockout message without swallowing
            self.lbl_error.setText(str(pe))
            self.txt_password.clear()
