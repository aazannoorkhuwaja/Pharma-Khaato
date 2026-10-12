"""Cash-shift and drawer reconciliation screen for Pharma-Khaato."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QMessageBox
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
    """Start a new cash shift with the amount currently in the drawer."""

    def __init__(self, employee_id: int, parent=None):
        super().__init__(parent)
        self.employee_id = employee_id

        self.setWindowTitle("Start Cash Shift")
        configure_dialog(self, 480, 330, minimum_width=390, minimum_height=280)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
            QLabel {{ font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; }}
            QDoubleSpinBox {{
                background-color: {ThemeTokens.SURFACE_BASE};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                padding: 4px 10px;
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Start Shift")
        title.setObjectName("h2")
        title.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        sub = QLabel("Enter the cash already in the drawer before you begin taking payments.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(sub)

        form = QFormLayout()
        self.spn_opening = QDoubleSpinBox()
        self.spn_opening.setRange(0.0, 500000.0)
        self.spn_opening.setValue(5000.0)
        self.spn_opening.setPrefix("Rs. ")
        self.spn_opening.setDecimals(2)
        self.spn_opening.setAccessibleName("Starting cash in drawer")
        form.addRow("Starting cash:", self.spn_opening)
        layout.addLayout(form)
        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        self.btn_open = QPushButton("Start Shift")
        self.btn_open.setObjectName("primaryButton")
        self.btn_open.clicked.connect(self.on_open)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_open)
        layout.addLayout(btn_box)

    def on_open(self):
        ok, res = _CASH_CONTROLLER.open_session(self.employee_id, self.spn_opening.value())
        if ok:
            parent_target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(parent_target, "Cash shift started.", ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Start Shift", str(res))


class RecordMovementDialog(QDialog):
    """Record cash added to or removed from the active drawer."""

    def __init__(self, session_id: int, employee_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.employee_id = employee_id

        self.setWindowTitle("Add / Remove Cash")
        configure_dialog(self, 520, 390, minimum_width=410, minimum_height=320)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
            QLabel {{ font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; }}
            QLineEdit, QComboBox, QDoubleSpinBox {{
                background-color: {ThemeTokens.SURFACE_BASE};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                padding: 4px 10px;
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Add / Remove Cash")
        title.setObjectName("h2")
        title.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        helper = QLabel("Use this for drawer cash that is not a normal sale, such as petty cash or added change.")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(helper)

        form = QFormLayout()
        self.cmb_type = QComboBox()
        for display_label, backend_value in CASH_MOVEMENT_OPTIONS:
            self.cmb_type.addItem(display_label, backend_value)
        form.addRow("Type:", self.cmb_type)

        self.spn_amount = QDoubleSpinBox()
        self.spn_amount.setRange(1.0, 1000000.0)
        self.spn_amount.setValue(500.0)
        self.spn_amount.setPrefix("Rs. ")
        self.spn_amount.setDecimals(2)
        self.spn_amount.setAccessibleName("Cash amount")
        form.addRow("Amount:", self.spn_amount)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("e.g. Supplier payment, petty cash, added change")
        self.txt_reason.setAccessibleName("Reason for cash entry")
        form.addRow("Note:", self.txt_reason)

        layout.addLayout(form)
        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Save Cash Entry")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def on_save(self):
        movement_type = self.cmb_type.currentData() or self.cmb_type.currentText()
        amount = self.spn_amount.value()
        reason = self.txt_reason.text().strip()
        if not reason:
            show_toast(self, "Add a short note explaining this cash entry.", ToastType.WARNING)
            return

        ok, msg = _CASH_CONTROLLER.record_movement(
            self.session_id,
            self.employee_id,
            movement_type,
            amount,
            reason,
        )
        if ok:
            parent_target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(parent_target, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Save Cash Entry", msg)


class CloseSessionDialog(QDialog):
    """Count the drawer and close the active shift safely."""

    def __init__(self, session_id: int, expected_cash: float, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.expected_cash = expected_cash

        self.setWindowTitle("Close Cash Shift")
        configure_dialog(self, 540, 430, minimum_width=420, minimum_height=350)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
            QLabel {{ font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; }}
            QLineEdit, QDoubleSpinBox {{
                background-color: {ThemeTokens.SURFACE_BASE};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                padding: 4px 10px;
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Count Cash & Close Shift")
        title.setObjectName("h2")
        title.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        lbl_exp = QLabel(f"Expected in drawer: Rs. {expected_cash:.2f}")
        lbl_exp.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.SUCCESS};")
        layout.addWidget(lbl_exp)

        form = QFormLayout()
        self.spn_actual = QDoubleSpinBox()
        self.spn_actual.setRange(0.0, 2000000.0)
        self.spn_actual.setValue(float(expected_cash))
        self.spn_actual.setPrefix("Rs. ")
        self.spn_actual.setDecimals(2)
        self.spn_actual.setAccessibleName("Counted cash in drawer")
        self.spn_actual.valueChanged.connect(self.update_discrepancy_label)
        form.addRow("Counted cash:", self.spn_actual)

        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Optional note about any difference")
        form.addRow("Notes:", self.txt_notes)
        layout.addLayout(form)

        self.lbl_disc = QLabel("Difference: Rs. 0.00 (Balanced)")
        self.lbl_disc.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.SUCCESS};")
        layout.addWidget(self.lbl_disc)
        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        self.btn_close_confirm = QPushButton("Close Shift")
        self.btn_close_confirm.setObjectName("dangerButton")
        self.btn_close_confirm.clicked.connect(self.on_close)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_close_confirm)
        layout.addLayout(btn_box)

    def update_discrepancy_label(self, value):
        difference = value - self.expected_cash
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
        actual = self.spn_actual.value()
        notes = self.txt_notes.text().strip() or "Standard shift close"
        ok, res = _CASH_CONTROLLER.close_session(self.session_id, actual, notes)
        if ok:
            parent_target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(parent_target, "Cash shift closed.", ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Close Shift", str(res))


class CashSessionScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self.active_session = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Shift & Cash",
            "Start or close the cash shift, record drawer changes, and balance the till."
        )
        self.pill_status = BadgePill("Shift Closed", BadgePill.TYPE_DANGER)
        header_card.add_pill(self.pill_status)
        layout.addWidget(header_card)

        self.control_card = Card()
        self.ctrl_layout = self.control_card.layout()

        self.lbl_session_info = QLabel("Checking shift status...")
        self.lbl_session_info.setWordWrap(True)
        self.lbl_session_info.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY};")
        self.ctrl_layout.addWidget(self.lbl_session_info, 1)

        self.btn_open_session = QPushButton("Start Shift")
        self.btn_open_session.setObjectName("successButton")
        self.btn_open_session.clicked.connect(self.open_new_session)

        self.btn_add_movement = QPushButton("Add / Remove Cash")
        self.btn_add_movement.setObjectName("primaryButton")
        self.btn_add_movement.clicked.connect(self.record_movement)

        self.btn_close_session = QPushButton("Close Shift")
        self.btn_close_session.setObjectName("dangerButton")
        self.btn_close_session.clicked.connect(self.close_current_session)

        self.ctrl_layout.addWidget(self.btn_open_session)
        self.ctrl_layout.addWidget(self.btn_add_movement)
        self.ctrl_layout.addWidget(self.btn_close_session)
        layout.addWidget(self.control_card)

        movements_card = Card()
        mov_layout = movements_card.layout()
        mov_layout.setSpacing(10)

        lbl_mov_hdr = QLabel("Recent Cash Activity")
        lbl_mov_hdr.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        mov_layout.addWidget(lbl_mov_hdr)

        self.tbl_movements = QTableWidget(0, 4)
        self.tbl_movements.setHorizontalHeaderLabels(["Type", "Amount", "Note", "Time"])
        self.tbl_movements.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_movements)
        self.tbl_movements.verticalHeader().setVisible(False)
        self.tbl_movements.setEditTriggers(QTableWidget.NoEditTriggers)
        mov_layout.addWidget(self.tbl_movements, 1)
        layout.addWidget(movements_card, 1)

        self.refresh_all_data()

    def on_screen_show(self):
        self.refresh_all_data()

    def get_current_employee_id(self) -> int:
        user = SessionState.get_instance().current_user
        if user and "id" in user:
            return user["id"]
        return 1

    def refresh_all_data(self):
        emp_id = self.get_current_employee_id()
        self.active_session = _CASH_CONTROLLER.active_session(emp_id)

        if self.active_session:
            session_id = self.active_session["id"]
            opening_cash, cash_sales, expected_cash = _CASH_CONTROLLER.expected_cash(session_id)

            self.pill_status.setText("Shift Open")
            self.pill_status.set_pill_type(BadgePill.TYPE_SUCCESS)
            self.lbl_session_info.setText(
                f"Started: {self.active_session['opened_at']}\n"
                f"Starting cash: Rs. {opening_cash:.2f}  •  Cash sales: Rs. {cash_sales:.2f}  •  "
                f"Expected in drawer: Rs. {expected_cash:.2f}"
            )

            self.btn_open_session.setVisible(False)
            self.btn_add_movement.setVisible(True)
            self.btn_close_session.setVisible(True)
        else:
            self.pill_status.setText("Shift Closed")
            self.pill_status.set_pill_type(BadgePill.TYPE_DANGER)
            self.lbl_session_info.setText(
                "No cash shift is open. Start a shift before taking payments."
            )
            self.btn_open_session.setVisible(True)
            self.btn_add_movement.setVisible(False)
            self.btn_close_session.setVisible(False)

        self.populate_movements_table()

    def populate_movements_table(self):
        try:
            rows = _CASH_CONTROLLER.recent_movements(50)
            self.tbl_movements.setRowCount(len(rows))
            for row, item in enumerate(rows):
                _movement_id, _session_id, movement_type, amount, reason, timestamp = item
                self.tbl_movements.setItem(
                    row, 0, QTableWidgetItem(CASH_MOVEMENT_LABELS.get(str(movement_type), str(movement_type)))
                )
                self.tbl_movements.setItem(row, 1, QTableWidgetItem(f"Rs. {float(amount):.2f}"))
                self.tbl_movements.setItem(row, 2, QTableWidgetItem(str(reason)))
                self.tbl_movements.setItem(row, 3, QTableWidgetItem(str(timestamp)))
        except Exception:
            self.tbl_movements.setRowCount(0)

    def open_new_session(self):
        dialog = OpenSessionDialog(self.get_current_employee_id(), self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def record_movement(self):
        if not self.active_session:
            show_toast(self, "Start a shift before recording drawer cash.", ToastType.WARNING)
            return
        dialog = RecordMovementDialog(
            self.active_session["id"],
            self.get_current_employee_id(),
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def close_current_session(self):
        if not self.active_session:
            return
        session_id = self.active_session["id"]
        _, _, expected_cash = _CASH_CONTROLLER.expected_cash(session_id)
        dialog = CloseSessionDialog(session_id, expected_cash, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()
