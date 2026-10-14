"""Pharma-Khaato first-run setup dialog.

The setup experience intentionally uses the same global design system as the rest
of the application. It is a short, task-focused form rather than a technical
configuration page, and remains comfortable on small or high-DPI displays.
"""

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox, QDoubleSpinBox,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt

from ui.widgets.toast import ToastType, show_toast
from ui.widgets.responsive import configure_dialog
from controllers.auth_controller import AuthController
from controllers.settings_controller import SettingsController

_AUTH_CONTROLLER = AuthController()
_SETTINGS_CONTROLLER = SettingsController()


class FirstRunWizardDialog(QDialog):
    """Collect only the information required to make the first login useful."""

    FORM_MAX_WIDTH = 960
    TWO_COLUMN_AT = 860

    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._wide_form = None

        self.setWindowTitle("Pharma-Khaato — Setup")
        configure_dialog(self, 980, 760, minimum_width=600, minimum_height=520)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)

        header = QWidget()
        header.setMaximumWidth(self.FORM_MAX_WIDTH)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        title = QLabel("Set up your pharmacy")
        title.setObjectName("h1")
        title.setProperty("uiTone", "accent")

        subtitle = QLabel(
            "Add the details shown on receipts, then create the administrator account. "
            "You can change pharmacy details later in Settings."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        required_note = QLabel("Fields marked * are required.")
        required_note.setObjectName("caption")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(required_note)
        root.addLayout(self._centered_row(header))

        self.scroll = QScrollArea()
        self.scroll.setObjectName("setupScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_body = QWidget()
        scroll_body.setObjectName("setupScrollBody")
        scroll_layout = QHBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(0)
        scroll_layout.addStretch(1)

        self.form_column = QWidget()
        self.form_column.setMaximumWidth(self.FORM_MAX_WIDTH)
        self.form_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        form_column_layout = QVBoxLayout(self.form_column)
        form_column_layout.setContentsMargins(0, 0, 0, 0)
        form_column_layout.setSpacing(14)

        pharmacy_card, pharmacy_body = self._section_card(
            "1", "Pharmacy details", "These details appear on receipts and reports."
        )
        self.pharmacy_grid = QGridLayout()
        self.pharmacy_grid.setContentsMargins(0, 0, 0, 0)
        self.pharmacy_grid.setHorizontalSpacing(16)
        self.pharmacy_grid.setVerticalSpacing(12)
        pharmacy_body.addLayout(self.pharmacy_grid)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Central Pharmacy")
        self.txt_name.setAccessibleName("Pharmacy Name")

        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("e.g. Main Road, Lahore")
        self.txt_address.setAccessibleName("Pharmacy Address")

        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("e.g. +92 300 1234567")
        self.txt_phone.setAccessibleName("Pharmacy Phone Number")

        self.txt_slogan = QLineEdit()
        self.txt_slogan.setPlaceholderText("Optional — short line for receipts")
        self.txt_slogan.setAccessibleName("Pharmacy Tagline")

        self.txt_license = QLineEdit()
        self.txt_license.setPlaceholderText("Optional — licence / registration number")
        self.txt_license.setAccessibleName("Pharmacy License Number")

        self.spn_tax = QDoubleSpinBox()
        self.spn_tax.setRange(0.0, 50.0)
        self.spn_tax.setDecimals(2)
        self.spn_tax.setValue(0.0)
        self.spn_tax.setSuffix(" %")
        self.spn_tax.setAccessibleName("Default Sales Tax Percentage")
        self.spn_tax.setToolTip(
            "Default tax used for new sales. You can change this later in Settings."
        )

        self._pharmacy_fields = [
            self._field("Pharmacy name", self.txt_name, required=True),
            self._field("Address", self.txt_address, required=True),
            self._field("Phone number", self.txt_phone, required=True),
            self._field("Tagline", self.txt_slogan, optional=True),
            self._field("Licence number", self.txt_license, optional=True),
            self._field("Default sales tax", self.spn_tax),
        ]
        form_column_layout.addWidget(pharmacy_card)

        admin_card, admin_body = self._section_card(
            "2",
            "Administrator account",
            "Use this account to manage staff, settings, and reports.",
        )
        self.admin_grid = QGridLayout()
        self.admin_grid.setContentsMargins(0, 0, 0, 0)
        self.admin_grid.setHorizontalSpacing(16)
        self.admin_grid.setVerticalSpacing(12)
        admin_body.addLayout(self.admin_grid)

        self.txt_fname = QLineEdit()
        self.txt_fname.setPlaceholderText("First name")
        self.txt_fname.setAccessibleName("Administrator First Name")

        self.txt_lname = QLineEdit()
        self.txt_lname.setPlaceholderText("Optional")
        self.txt_lname.setAccessibleName("Administrator Last Name")

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("e.g. admin")
        self.txt_user.setAccessibleName("Administrator Username")

        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("At least 8 characters")
        self.txt_pass.setAccessibleName("Administrator Password")

        self._admin_fields = [
            self._field("First name", self.txt_fname, required=True),
            self._field("Last name", self.txt_lname, optional=True),
            self._field("Username", self.txt_user, required=True),
            self._field(
                "Password",
                self.txt_pass,
                required=True,
                helper="Use at least 8 characters. A longer passphrase is fine.",
            ),
        ]
        form_column_layout.addWidget(admin_card)
        form_column_layout.addStretch(1)

        scroll_layout.addWidget(self.form_column, 10)
        scroll_layout.addStretch(1)
        self.scroll.setWidget(scroll_body)
        root.addWidget(self.scroll, 1)

        footer = QFrame()
        footer.setObjectName("setupFooter")
        footer.setMaximumWidth(self.FORM_MAX_WIDTH)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.setSpacing(12)

        footer_note = QLabel("Next: sign in with the administrator account you create here.")
        footer_note.setObjectName("caption")
        footer_note.setWordWrap(True)
        footer_layout.addWidget(footer_note, 1)

        self.btn_submit = QPushButton("Complete setup")
        self.btn_submit.setObjectName("primaryButton")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setMinimumWidth(170)
        self.btn_submit.clicked.connect(self.on_submit)
        footer_layout.addWidget(self.btn_submit, 0, Qt.AlignmentFlag.AlignRight)

        root.addLayout(self._centered_row(footer))

        self._apply_form_layout(force=True)
        self.txt_name.setFocus(Qt.FocusReason.OtherFocusReason)

    @staticmethod
    def _centered_row(widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(widget, 10)
        row.addStretch(1)
        return row

    @staticmethod
    def _section_card(step: str, title: str, description: str):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading_row.setSpacing(9)

        badge = QLabel(step)
        badge.setObjectName("badgePill")
        badge.setProperty("pillType", "success")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setMinimumWidth(26)
        badge.setAccessibleName(f"Step {step}")

        heading = QLabel(title)
        heading.setObjectName("h2")
        heading_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        heading_row.addWidget(heading, 1, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(heading_row)

        desc = QLabel(description)
        desc.setObjectName("subtitle")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        return card, layout

    @staticmethod
    def _field(
        label_text: str,
        editor: QWidget,
        *,
        required: bool = False,
        optional: bool = False,
        helper: str = None,
    ) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        suffix = " *" if required else (" (optional)" if optional else "")
        label = QLabel(label_text + suffix)
        label.setProperty("uiWeight", "semibold")
        label.setBuddy(editor)
        layout.addWidget(label)
        layout.addWidget(editor)

        if helper:
            hint = QLabel(helper)
            hint.setObjectName("caption")
            hint.setWordWrap(True)
            layout.addWidget(hint)
        return wrapper

    @staticmethod
    def _clear_grid(layout: QGridLayout) -> None:
        while layout.count():
            layout.takeAt(0)

    def _apply_form_layout(self, *, force: bool = False) -> None:
        wide = self.width() >= self.TWO_COLUMN_AT
        if not force and wide == self._wide_form:
            return
        self._wide_form = wide

        self._clear_grid(self.pharmacy_grid)
        self._clear_grid(self.admin_grid)

        if wide:
            self.pharmacy_grid.addWidget(self._pharmacy_fields[0], 0, 0, 1, 2)
            self.pharmacy_grid.addWidget(self._pharmacy_fields[1], 1, 0, 1, 2)
            self.pharmacy_grid.addWidget(self._pharmacy_fields[2], 2, 0)
            self.pharmacy_grid.addWidget(self._pharmacy_fields[4], 2, 1)
            self.pharmacy_grid.addWidget(self._pharmacy_fields[3], 3, 0)
            self.pharmacy_grid.addWidget(self._pharmacy_fields[5], 3, 1)

            self.admin_grid.addWidget(self._admin_fields[0], 0, 0)
            self.admin_grid.addWidget(self._admin_fields[1], 0, 1)
            self.admin_grid.addWidget(self._admin_fields[2], 1, 0)
            self.admin_grid.addWidget(self._admin_fields[3], 1, 1)
            self.pharmacy_grid.setColumnStretch(0, 1)
            self.pharmacy_grid.setColumnStretch(1, 1)
            self.admin_grid.setColumnStretch(0, 1)
            self.admin_grid.setColumnStretch(1, 1)
        else:
            for row, field in enumerate(self._pharmacy_fields):
                self.pharmacy_grid.addWidget(field, row, 0)
            for row, field in enumerate(self._admin_fields):
                self.admin_grid.addWidget(field, row, 0)
            self.pharmacy_grid.setColumnStretch(0, 1)
            self.admin_grid.setColumnStretch(0, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_form_layout()

    def _warn_and_focus(self, widget: QWidget, message: str) -> None:
        if self.show_message_box:
            QMessageBox.warning(self, "Check this field", message)
        widget.setFocus(Qt.FocusReason.OtherFocusReason)

    def on_submit(self):
        name = self.txt_name.text().strip()
        address = self.txt_address.text().strip()
        phone = self.txt_phone.text().strip()
        fname = self.txt_fname.text().strip()
        username = self.txt_user.text().strip()
        password = self.txt_pass.text()

        if not name:
            self._warn_and_focus(self.txt_name, "Enter the pharmacy name to continue.")
            return
        if not address:
            self._warn_and_focus(self.txt_address, "Enter the pharmacy address to continue.")
            return
        if not phone:
            self._warn_and_focus(self.txt_phone, "Enter the pharmacy phone number to continue.")
            return
        if not fname:
            self._warn_and_focus(self.txt_fname, "Enter the administrator's first name.")
            return
        if not username:
            self._warn_and_focus(self.txt_user, "Choose a username for the administrator account.")
            return
        if not password:
            self._warn_and_focus(self.txt_pass, "Create a password for the administrator account.")
            return
        if len(password) < 8:
            self._warn_and_focus(self.txt_pass, "Use a password with at least 8 characters.")
            return

        settings = {
            "pharmacy_name": name,
            "slogan": self.txt_slogan.text().strip(),
            "address": address,
            "phone": phone,
            "license_number": self.txt_license.text().strip(),
            "default_tax_rate": str(self.spn_tax.value()),
        }
        if not _SETTINGS_CONTROLLER.update(settings):
            if self.show_message_box:
                QMessageBox.critical(
                    self,
                    "Could not save pharmacy details",
                    "The pharmacy settings could not be saved. Please try again.",
                )
            return

        ok, msg = _AUTH_CONTROLLER.register_initial_admin(
            username,
            password,
            fname,
            self.txt_lname.text().strip(),
        )
        if not ok and "already in use" not in msg:
            if self.show_message_box:
                QMessageBox.critical(self, "Could not create administrator", msg)
            return

        if self.show_message_box:
            show_toast(
                self,
                "Setup complete. Sign in to start using Pharma-Khaato.",
                ToastType.SUCCESS,
            )
        self.accept()
