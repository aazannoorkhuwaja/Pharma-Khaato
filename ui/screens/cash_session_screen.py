"""Cash-shift and drawer reconciliation screen."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QMessageBox,
)

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.app.state.session_state import SessionState
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog
from controllers.cash_session_controller import CashSessionController
from ui.ux_copy import CASH_MOVEMENT_OPTIONS, CASH_MOVEMENT_LABELS

_CASH_CONTROLLER = CashSessionController()


class OpenSessionDialog(QDialog):
    def __init__(self, employee_id: int, parent=None):
        super().__init__(parent)
        self.employee_id = employee_id
        self.setWindowTitle("Start Cash Shift")
        configure_dialog(self, 480, 320, minimum_width=390, minimum_height=270)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Start Shift")
        title.setObjectName("h2")
        layout.addWidget(title)
        help_text = QLabel("Enter the physical cash already in the drawer before taking payments.")
        help_text.setWordWrap(True)
        help_text.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(help_text)

        form = QFormLayout()
        self.spn_opening = QDoubleSpinBox()
        self.spn_opening.setRange(0.0, 500000.0)
        self.spn_opening.setValue(5000.0)
        self.spn_opening.setPrefix("Rs. ")
        self.spn_opening.setDecimals(2)
        form.addRow("Starting cash:", self.spn_opening)
        layout.addLayout(form)

        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        start = QPushButton("Start Shift")
        start.setObjectName("primaryButton")
        start.clicked.connect(self.on_open)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(start)
        layout.addLayout(row)

    def on_open(self):
        ok, result = _CASH_CONTROLLER.open_session(self.employee_id, self.spn_opening.value())
        if ok:
            show_toast(self.parent() or self, "Cash shift started.", ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Start Shift", str(result))


class RecordMovementDialog(QDialog):
    def __init__(self, session_id: int, employee_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.employee_id = employee_id
        self.setWindowTitle("Add / Remove Cash")
        configure_dialog(self, 520, 390, minimum_width=410, minimum_height=320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Add / Remove Cash")
        title.setObjectName("h2")
        layout.addWidget(title)
        helper = QLabel("Use this only for physical drawer cash that is not a normal sale or credit repayment.")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(helper)

        form = QFormLayout()
        self.cmb_type = QComboBox()
        for label, value in CASH_MOVEMENT_OPTIONS:
            self.cmb_type.addItem(label, value)
        form.addRow("Type:", self.cmb_type)

        self.spn_amount = QDoubleSpinBox()
        self.spn_amount.setRange(1.0, 1000000.0)
        self.spn_amount.setValue(500.0)
        self.spn_amount.setPrefix("Rs. ")
        self.spn_amount.setDecimals(2)
        form.addRow("Amount:", self.spn_amount)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("e.g. Petty cash, supplier payment, added change")
        self.txt_reason.setMaxLength(250)
        form.addRow("Note *:", self.txt_reason)
        layout.addLayout(form)

        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Cash Entry")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.on_save)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(save)
        layout.addLayout(row)

    def on_save(self):
        reason = self.txt_reason.text().strip()
        if not reason:
            show_toast(self, "Add a short note explaining this cash entry.", ToastType.WARNING)
            return
        ok, msg = _CASH_CONTROLLER.record_movement(
            self.session_id,
            self.employee_id,
            self.cmb_type.currentData() or self.cmb_type.currentText(),
            self.spn_amount.value(),
            reason,
        )
        if ok:
            show_toast(self.parent() or self, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Save Cash Entry", msg)


class CloseSessionDialog(QDialog):
    def __init__(self, session_id: int, expected_cash: float, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.expected_cash = expected_cash
        self.setWindowTitle("Close Cash Shift")
        configure_dialog(self, 540, 420, minimum_width=420, minimum_height=340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Count Cash & Close Shift")
        title.setObjectName("h2")
        layout.addWidget(title)
        expected = QLabel(f"Expected physical cash: Rs. {expected_cash:.2f}")
        expected.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.SUCCESS};")
        layout.addWidget(expected)

        form = QFormLayout()
        self.spn_actual = QDoubleSpinBox()
        self.spn_actual.setRange(0.0, 2000000.0)
        self.spn_actual.setValue(float(expected_cash))
        self.spn_actual.setPrefix("Rs. ")
        self.spn_actual.setDecimals(2)
        self.spn_actual.valueChanged.connect(self.update_discrepancy_label)
        form.addRow("Counted cash:", self.spn_actual)
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Optional note about any difference")
        form.addRow("Notes:", self.txt_notes)
        layout.addLayout(form)

        self.lbl_disc = QLabel("Difference: Rs. 0.00 (Balanced)")
        layout.addWidget(self.lbl_disc)
        self.update_discrepancy_label(self.spn_actual.value())

        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        close = QPushButton("Close Shift")
        close.setObjectName("dangerButton")
        close.clicked.connect(self.on_close)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(close)
        layout.addLayout(row)

    def update_discrepancy_label(self, value):
        difference = float(value) - self.expected_cash
        if abs(difference) < 0.01:
            self.lbl_disc.setText("Difference: Rs. 0.00 (Balanced)")
            self.lbl_disc.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.SUCCESS};")
        elif difference > 0:
            self.lbl_disc.setText(f"Difference: +Rs. {difference:.2f} (Over)")
            self.lbl_disc.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.WARNING};")
        else:
            self.lbl_disc.setText(f"Difference: -Rs. {abs(difference):.2f} (Short)")
            self.lbl_disc.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.DANGER};")

    def on_close(self):
        ok, result = _CASH_CONTROLLER.close_session(
            self.session_id,
            self.spn_actual.value(),
            self.txt_notes.text().strip() or "Standard shift close",
        )
        if ok:
            show_toast(self.parent() or self, "Cash shift closed.", ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Close Shift", str(result))


class CashSessionScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self.active_session = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = ScreenHeader(
            "Shift & Cash",
            "Track only physical drawer cash. Card and wallet payments stay outside the till."
        )
        self.pill_status = BadgePill("Shift Closed", BadgePill.TYPE_DANGER)
        header.add_pill(self.pill_status)
        layout.addWidget(header)

        control = Card()
        control_layout = control.layout()
        control_layout.setSpacing(10)
        self.lbl_session_info = QLabel("Checking shift status...")
        self.lbl_session_info.setWordWrap(True)
        control_layout.addWidget(self.lbl_session_info)

        buttons = QHBoxLayout()
        self.btn_open_session = QPushButton("Start Shift")
        self.btn_open_session.setObjectName("successButton")
        self.btn_open_session.clicked.connect(self.open_new_session)
        self.btn_add_movement = QPushButton("Add / Remove Cash")
        self.btn_add_movement.setObjectName("primaryButton")
        self.btn_add_movement.clicked.connect(self.record_movement)
        self.btn_close_session = QPushButton("Close Shift")
        self.btn_close_session.setObjectName("dangerButton")
        self.btn_close_session.clicked.connect(self.close_current_session)
        buttons.addWidget(self.btn_open_session)
        buttons.addWidget(self.btn_add_movement)
        buttons.addWidget(self.btn_close_session)
        buttons.addStretch()
        control_layout.addLayout(buttons)
        layout.addWidget(control)

        movement_card = Card()
        movement_layout = movement_card.layout()
        movement_layout.addWidget(QLabel("This Shift’s Manual Cash Entries"))
        self.tbl_movements = QTableWidget(0, 4)
        self.tbl_movements.setHorizontalHeaderLabels(["Type", "Amount", "Note", "Time"])
        self.tbl_movements.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_movements)
        self.tbl_movements.verticalHeader().setVisible(False)
        self.tbl_movements.setEditTriggers(QTableWidget.NoEditTriggers)
        movement_layout.addWidget(self.tbl_movements, 1)
        layout.addWidget(movement_card, 1)
        self.refresh_all_data()

    def get_current_employee_id(self) -> int:
        user = SessionState.get_instance().current_user
        return int(user["id"]) if user and "id" in user else 1

    def on_screen_show(self):
        self.refresh_all_data()

    def refresh_all_data(self):
        emp_id = self.get_current_employee_id()
        self.active_session = _CASH_CONTROLLER.active_session(emp_id)
        if self.active_session:
            summary = _CASH_CONTROLLER.cash_summary(self.active_session["id"]) or {}
            self.pill_status.setText("Shift Open")
            self.pill_status.set_pill_type(BadgePill.TYPE_SUCCESS)
            self.lbl_session_info.setText(
                f"Started: {self.active_session['opened_at']}\n"
                f"Starting cash: Rs. {float(summary.get('opening_cash', 0)):.2f}  •  "
                f"Cash sales: Rs. {float(summary.get('cash_sales', 0)):.2f}  •  "
                f"Cash credit collected: Rs. {float(summary.get('cash_credit_collections', 0)):.2f}\n"
                f"Cash in: Rs. {float(summary.get('cash_in', 0)):.2f}  •  "
                f"Cash out: Rs. {float(summary.get('cash_out', 0)):.2f}  •  "
                f"Refund cash: Rs. {float(summary.get('refunds', 0)):.2f}  •  "
                f"Expected in drawer: Rs. {float(summary.get('expected_cash', 0)):.2f}"
            )
            self.btn_open_session.hide()
            self.btn_add_movement.show()
            self.btn_close_session.show()
        else:
            self.pill_status.setText("Shift Closed")
            self.pill_status.set_pill_type(BadgePill.TYPE_DANGER)
            self.lbl_session_info.setText("No cash shift is open. Start one before taking physical cash payments.")
            self.btn_open_session.show()
            self.btn_add_movement.hide()
            self.btn_close_session.hide()
        self.populate_movements_table()

    def populate_movements_table(self):
        current_id = self.active_session["id"] if self.active_session else None
        try:
            rows = _CASH_CONTROLLER.recent_movements(100)
            if current_id is not None:
                rows = [item for item in rows if int(item[1]) == int(current_id)][:50]
            else:
                rows = []
            self.tbl_movements.setUpdatesEnabled(False)
            self.tbl_movements.setRowCount(len(rows))
            for row, item in enumerate(rows):
                _movement_id, _session_id, movement_type, amount, reason, timestamp = item
                self.tbl_movements.setItem(row, 0, QTableWidgetItem(CASH_MOVEMENT_LABELS.get(str(movement_type), str(movement_type))))
                self.tbl_movements.setItem(row, 1, QTableWidgetItem(f"Rs. {float(amount):.2f}"))
                self.tbl_movements.setItem(row, 2, QTableWidgetItem(str(reason)))
                self.tbl_movements.setItem(row, 3, QTableWidgetItem(str(timestamp)))
        except Exception:
            self.tbl_movements.setRowCount(0)
        finally:
            self.tbl_movements.setUpdatesEnabled(True)

    def open_new_session(self):
        dialog = OpenSessionDialog(self.get_current_employee_id(), self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def record_movement(self):
        if not self.active_session:
            show_toast(self, "Start a shift before recording drawer cash.", ToastType.WARNING)
            return
        dialog = RecordMovementDialog(self.active_session["id"], self.get_current_employee_id(), self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def close_current_session(self):
        if not self.active_session:
            return
        summary = _CASH_CONTROLLER.cash_summary(self.active_session["id"]) or {}
        dialog = CloseSessionDialog(
            self.active_session["id"],
            float(summary.get("expected_cash", 0.0)),
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()
