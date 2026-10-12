"""
ManagerAuthModal — dialog collecting manager credentials for high discounts.
Works with core/manager_auth_service.enforce_discount_policy().
File: ui/widgets/manager_auth_modal.py
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt

from controllers.manager_auth_controller import ManagerAuthController
from ui.widgets.responsive import configure_dialog

_MANAGER_AUTH_CONTROLLER = ManagerAuthController()


class ManagerAuthModal(QDialog):
    def __init__(self, discount_amount: float, subtotal: float, parent=None):
        super().__init__(parent)
        self.discount_amount = discount_amount
        self.subtotal = subtotal
        self.authorized_by = None  # display name when approved

        self.setWindowTitle("Manager Approval")
        configure_dialog(self, 450, 320, minimum_width=380, minimum_height=260)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl = QLabel(
            f"This discount (Rs. {discount_amount:.2f}) is above the cashier limit "
            f"({_MANAGER_AUTH_CONTROLLER.discount_threshold_pct:.0f}%).<br><br>"
            "A manager or administrator must sign in to approve it."
        )
        lbl.setTextFormat(Qt.RichText)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.txt_user = QLineEdit(self)
        self.txt_user.setPlaceholderText("Manager username")
        layout.addWidget(self.txt_user)

        self.txt_pass = QLineEdit(self)
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_pass.setPlaceholderText("Manager password")
        layout.addWidget(self.txt_pass)

        btn = QPushButton("Approve Discount", self)
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self._verify)
        layout.addWidget(btn)

        self.error = QLabel("", self)
        self.error.setStyleSheet("color: #d9534f;")
        layout.addWidget(self.error)

        self.txt_user.setFocus()

    def _verify(self):
        emp_id, who = _MANAGER_AUTH_CONTROLLER.verify(self.txt_user.text(), self.txt_pass.text())
        if emp_id is not None:
            self.authorized_by = who
            self.accept()
        else:
            self.error.setText(who or "Approval failed. Check the manager username and password.")
            self.txt_pass.clear()
            self.txt_pass.setFocus()
