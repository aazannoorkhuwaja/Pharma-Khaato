"""Pharma Khaato sign-in dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QWidget, QMessageBox
)
from PySide6.QtCore import Qt

from config import ApplicationSettings
from controllers.auth_controller import AuthController
from ui.theme.tokens import ThemeTokens
from ui.app.state.session_state import SessionState
from ui.widgets.responsive import configure_dialog
from ui.app.async_tasks import AsyncTaskRunner

_AUTH_CONTROLLER = AuthController()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{ApplicationSettings.DISPLAY_NAME} — Sign In")
        configure_dialog(self, 520, 620, minimum_width=400, minimum_height=500)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.user_data = None
        self._tasks = AsyncTaskRunner(self)
        self._signing_in = False

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
            QLineEdit {{
                background-color: {ThemeTokens.SURFACE_BASE};
                color: {ThemeTokens.TEXT_PRIMARY};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                padding: 4px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ThemeTokens.BORDER_FOCUS};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        title = QLabel("PHARMA KHAATO")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 800; letter-spacing: 1px;")

        product_line = QLabel(ApplicationSettings.PRODUCT_TAGLINE)
        product_line.setObjectName("subtitle")
        product_line.setAlignment(Qt.AlignCenter)
        product_line.setWordWrap(True)

        subtitle = QLabel("Use the owner or staff account created for this shop")
        subtitle.setObjectName("caption")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-weight: 500;")

        card_layout.addWidget(title)
        card_layout.addWidget(product_line)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)

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
        self.btn_submit = btn_submit
        btn_submit.setObjectName("primaryButton")
        btn_submit.setCursor(Qt.PointingHandCursor)
        btn_submit.clicked.connect(self.handle_login)
        login_layout.addWidget(btn_submit)
        self.btn_sign_in_help = QPushButton("First time here or can’t sign in?")
        self.btn_sign_in_help.clicked.connect(self.show_sign_in_help)
        login_layout.addWidget(self.btn_sign_in_help)
        login_layout.addStretch()

        card_layout.addWidget(login_container)

        footer = QLabel(
            f"Version {ApplicationSettings.APP_VERSION}  •  Local-first desktop software\n"
            "Your pharmacy records remain on this workstation unless they are exported or backed up."
        )
        footer.setObjectName("caption")
        footer.setAlignment(Qt.AlignCenter)
        footer.setWordWrap(True)
        footer.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        card_layout.addWidget(footer)

        layout.addWidget(card)

    def show_sign_in_help(self):
        QMessageBox.information(self, "Help signing in",
            "Use the username and password created for this shop. There is no default password.\n\n"
            "An older installation may already have an account on this computer. "
            "Reinstalling keeps that account and the shop records.\n\n"
            "If you are a staff member, ask the owner to reset your password in Settings → Staff Access. "
            "If the owner cannot sign in, contact support before changing any files.\n\n"
            "Do not delete the shop data folder to fix a sign-in problem.")

    def handle_login(self):
        if self._signing_in:
            return
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        if not username or not password:
            self.lbl_error.setText("Enter your username and password.")
            return

        self._signing_in = True
        self.btn_submit.setEnabled(False)
        self.btn_submit.setText('Signing in…')
        self.lbl_error.setText('')
        self.txt_username.setEnabled(False)
        self.txt_password.setEnabled(False)
        def authenticate():
            try:
                return _AUTH_CONTROLLER.login(username,password),None
            except PermissionError as exc:
                return None,str(exc)
        def complete(result):
            self._signing_in = False
            self.btn_submit.setEnabled(True)
            self.btn_submit.setText('Sign In')
            self.txt_username.setEnabled(True)
            self.txt_password.setEnabled(True)
            res,error = result
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
                self.lbl_error.setText(error or "Username or password is incorrect.")
                self.txt_password.clear()
                self.txt_password.setFocus()
        def failed(_details):
            complete((None,'The shop could not be reached. Check the connection and sign in again.'))
        self._tasks.run(authenticate,complete,failed)

    def reject(self):
        if not self._signing_in:
            super().reject()
