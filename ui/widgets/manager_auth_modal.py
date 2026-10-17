"""
ManagerAuthModal — dialog collecting manager credentials for high discounts.
Works with core/manager_auth_service.enforce_discount_policy().
File: ui/widgets/manager_auth_modal.py
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt

from controllers.manager_auth_controller import ManagerAuthController
from ui.widgets.responsive import configure_dialog
from ui.app.async_tasks import AsyncTaskRunner

_MANAGER_AUTH_CONTROLLER = ManagerAuthController()


class ManagerAuthModal(QDialog):
    def __init__(self, discount_amount: float, subtotal: float, parent=None, employee_id=None):
        super().__init__(parent)
        self.discount_amount = discount_amount
        self.subtotal = subtotal
        self.authorized_by = None  # display name when approved
        self.approval_token = None
        self.employee_id = employee_id
        self._tasks = AsyncTaskRunner(self)
        self._approval_pending = False
        self._closed = False
        self.finished.connect(lambda _code: setattr(self, "_closed", True))

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

        self.btn_approve = QPushButton("Approve Discount", self)
        self.btn_approve.setObjectName("primaryButton")
        self.btn_approve.clicked.connect(self._verify)
        layout.addWidget(self.btn_approve)

        self.error = QLabel("", self)
        self.error.setStyleSheet("color: #d9534f;")
        layout.addWidget(self.error)

        self.txt_user.setFocus()

    def _verify(self):
        if self._approval_pending:
            return
        if self.employee_id is None:
            from ui.app.state.session_state import SessionState
            user = SessionState.get_instance().current_user or {}
            self.employee_id = user.get("id") or user.get("emp_id")
        username, password = self.txt_user.text(), self.txt_pass.text()
        self.txt_pass.clear()
        self._approval_pending = True
        self.btn_approve.setEnabled(False)
        self.error.setText("Checking approval…")
        self._tasks.run(lambda: _MANAGER_AUTH_CONTROLLER.issue_discount_approval(username, password, self.employee_id,
                                             self.discount_amount, self.subtotal), self._approval_finished,
                        lambda _details: self._approval_finished((None, "Approval is unavailable. Try again.")))

    def _approval_finished(self, result):
        if self._closed:
            return
        self._approval_pending = False
        self.btn_approve.setEnabled(True)
        token, who = result
        if token is not None:
            self.approval_token = token
            self.authorized_by = who
            self.accept()
        else:
            self.error.setText(who or "Approval failed. Check the manager username and password.")
            self.txt_pass.clear()
            self.txt_pass.setFocus()
