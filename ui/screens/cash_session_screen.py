from ui.widgets.semantic_style import set_tone
"""Cash-shift and drawer reconciliation screen."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QMessageBox, QCheckBox,
)

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.app.async_tasks import AsyncTaskRunner
from ui.app.state.session_state import SessionState
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog
from controllers.cash_session_controller import CashSessionController
from ui.ux_copy import CASH_MOVEMENT_OPTIONS, CASH_MOVEMENT_LABELS

_CASH_CONTROLLER = CashSessionController()


class CashOperationDialog(QDialog):
    def reject(self):
        if not getattr(self,'_saving',False):
            super().reject()

    def closeEvent(self,event):
        if getattr(self,'_saving',False):
            event.ignore()
        else:
            super().closeEvent(event)


class OpenSessionDialog(CashOperationDialog):
    def __init__(self, employee_id: int, parent=None):
        super().__init__(parent)
        self.employee_id = employee_id
        self._tasks = AsyncTaskRunner(self)
        self._saving = False
        self.setWindowTitle("Start Cash Shift")
        configure_dialog(self, 480, 320, minimum_width=390, minimum_height=270)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Start Shift")
        title.setObjectName("h2")
        layout.addWidget(title)
        help_text = QLabel("Count the cash in the drawer and enter that amount.")
        help_text.setWordWrap(True)
        set_tone(help_text, "muted")
        layout.addWidget(help_text)

        form = QFormLayout()
        self.spn_opening = QDoubleSpinBox()
        self.spn_opening.setRange(0.0, 500000.0)
        self.spn_opening.setValue(0.0)
        self.spn_opening.setPrefix("Rs. ")
        self.spn_opening.setDecimals(2)
        form.addRow("Starting cash:", self.spn_opening)
        layout.addLayout(form)

        row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_start = QPushButton("Start Shift")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.clicked.connect(self.on_open)
        row.addStretch()
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_start)
        layout.addLayout(row)

    def on_open(self):
        if self._saving:
            return
        opening_cash = self.spn_opening.value()
        self._saving = True
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_start.setText("Starting…")
        self._tasks.run(
            lambda: _CASH_CONTROLLER.open_session(self.employee_id, opening_cash),
            self._open_complete,
            lambda _details: self._open_failed(),
        )

    def _open_complete(self, result):
        self._saving = False
        ok, value = result
        if ok:
            SessionState.get_instance().set_cash_session({"id": value})
            show_toast(self.parent() or self, "Cash shift started.", ToastType.SUCCESS)
            self.accept()
            return
        self.btn_start.setText("Start Shift")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Could Not Start Shift", str(value))

    def _open_failed(self):
        self._saving = False
        self.btn_start.setText("Start Shift")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Could Not Start Shift", "The shift could not be started. Try again.")


class RecordMovementDialog(CashOperationDialog):
    def __init__(self, session_id: int, employee_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.employee_id = employee_id
        self._tasks = AsyncTaskRunner(self)
        self._saving = False
        self.setWindowTitle("Add / Remove Cash")
        configure_dialog(self, 520, 390, minimum_width=410, minimum_height=320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Add / Remove Cash")
        title.setObjectName("h2")
        layout.addWidget(title)
        helper = QLabel("Record cash added to or taken from the drawer. Do not enter sales or customer payments here.")
        helper.setWordWrap(True)
        set_tone(helper, "muted")
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
        self.txt_reason.setPlaceholderText("e.g. Cash added for change, or cash taken for shop expenses")
        self.txt_reason.setMaxLength(250)
        form.addRow("Note *:", self.txt_reason)
        layout.addLayout(form)

        row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save Cash Entry")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.on_save)
        row.addStretch()
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        layout.addLayout(row)

    def on_save(self):
        if self._saving:
            return
        reason = self.txt_reason.text().strip()
        if not reason:
            show_toast(self, "Add a short note explaining this cash entry.", ToastType.WARNING)
            return
        args = (
            self.session_id,
            self.employee_id,
            self.cmb_type.currentData() or self.cmb_type.currentText(),
            self.spn_amount.value(),
            reason,
        )
        self._saving = True
        self.btn_save.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_save.setText("Saving…")
        self._tasks.run(
            lambda: _CASH_CONTROLLER.record_movement(*args),
            self._save_complete,
            lambda _details: self._save_failed(),
        )

    def _save_complete(self, result):
        self._saving = False
        ok, msg = result
        if ok:
            show_toast(self.parent() or self, msg, ToastType.SUCCESS)
            self.accept()
            return
        self.btn_save.setText("Save Cash Entry")
        self.btn_save.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Could Not Save Cash Entry", msg)

    def _save_failed(self):
        self._saving = False
        self.btn_save.setText("Save Cash Entry")
        self.btn_save.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Could Not Save Cash Entry", "The cash entry could not be saved. Try again.")


class CloseSessionDialog(CashOperationDialog):
    def __init__(self, session_id: int, expected_cash: float, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.expected_cash = expected_cash
        self._tasks = AsyncTaskRunner(self)
        self._saving = False
        self.setWindowTitle("Close Cash Shift")
        configure_dialog(self, 540, 420, minimum_width=420, minimum_height=340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("Count Cash & Close Shift")
        title.setObjectName("h2")
        layout.addWidget(title)
        expected = QLabel(f"Cash expected in drawer: Rs. {expected_cash:.2f}")
        expected.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.SUCCESS};")
        layout.addWidget(expected)

        form = QFormLayout()
        self.spn_actual = QDoubleSpinBox()
        self.spn_actual.setRange(0.0, 2000000.0)
        self.spn_actual.setValue(0.0)
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
        self.confirm_count = QCheckBox('I have counted the physical cash in the drawer')
        layout.addWidget(self.confirm_count)
        self.confirm_difference = QCheckBox('I acknowledge this cash shortage or overage')
        layout.addWidget(self.confirm_difference)

        row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_close = QPushButton("Close Shift")
        self.btn_close.setObjectName("dangerButton")
        self.btn_close.clicked.connect(self.on_close)
        self.confirm_count.toggled.connect(self._update_close_enabled)
        self.confirm_difference.toggled.connect(self._update_close_enabled)
        self.spn_actual.valueChanged.connect(self._count_changed)
        self._count_changed()
        row.addStretch()
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_close)
        layout.addLayout(row)

    def _count_changed(self, *_):
        self.confirm_count.setChecked(False)
        self.confirm_difference.setChecked(False)
        self.confirm_difference.setVisible(abs(self.spn_actual.value() - self.expected_cash) >= .01)
        self._update_close_enabled()

    def _update_close_enabled(self, *_):
        difference = abs(self.spn_actual.value() - self.expected_cash) >= .01
        self.btn_close.setEnabled(not self._saving and self.confirm_count.isChecked()
                                  and (not difference or self.confirm_difference.isChecked()))

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
        if self._saving:
            return
        if not self.confirm_count.isChecked():
            QMessageBox.information(self,'Count Cash First','Count the money in the drawer, enter that amount, and confirm the count.')
            return
        if abs(self.spn_actual.value() - self.expected_cash) >= .01 and not self.confirm_difference.isChecked():
            return
        actual = self.spn_actual.value()
        notes = self.txt_notes.text().strip() or "Standard shift close"
        self._saving = True
        self.btn_close.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_close.setText("Closing…")
        self._tasks.run(
            lambda: _CASH_CONTROLLER.close_session(self.session_id, actual, notes),
            self._close_complete,
            lambda _details: self._close_failed(),
        )

    def _close_complete(self, result):
        self._saving = False
        ok, value = result
        if ok:
            SessionState.get_instance().set_cash_session(None)
            show_toast(self.parent() or self, "Cash shift closed.", ToastType.SUCCESS)
            self.accept()
            return
        self.btn_close.setText("Close Shift")
        self._update_close_enabled()
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Could Not Close Shift", str(value))

    def _close_failed(self):
        self._saving = False
        self.btn_close.setText("Close Shift")
        self._update_close_enabled()
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Could Not Close Shift", "The shift could not be closed. Try again.")


class CashSessionScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self.active_session = None
        self._current_summary = {}
        self._tasks = AsyncTaskRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = ScreenHeader(
            "Shift & Cash",
            "Track only physical drawer cash. Card and wallet payments stay outside the till."
        )
        self.pill_status = BadgePill("Checking Shift", BadgePill.TYPE_INFO)
        header.add_pill(self.pill_status)
        layout.addWidget(header)

        control = Card()
        control_layout = control.layout()
        control_layout.setSpacing(10)
        self.lbl_session_info = QLabel("Checking shift status…")
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
        self.btn_pending = QPushButton('Check Last Cash Entry')
        self.btn_pending.clicked.connect(self.recover_pending_entry)
        buttons.addWidget(self.btn_pending)
        buttons.addStretch()
        control_layout.addLayout(buttons)
        layout.addWidget(control)
        self.lbl_last_close = QLabel()
        self.lbl_last_close.setWordWrap(True)
        layout.addWidget(self.lbl_last_close)

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

    def recover_pending_entry(self):
        self.btn_pending.setEnabled(False)
        def complete(result):
            self.btn_pending.setEnabled(True)
            if not result[0]:
                QMessageBox.warning(self,'Cash Entry Not Saved',str(result[1]))
            else:
                show_toast(self,'The previous cash entry has been checked. Refresh the drawer totals.',ToastType.SUCCESS)
            self.refresh_all_data()
        self._tasks.run(lambda:_CASH_CONTROLLER.recover_pending(self.get_current_employee_id()),complete,
                        lambda _details:self._pending_failed())

    def _pending_failed(self):
        self.btn_pending.setEnabled(True)
        QMessageBox.warning(self,'Cash Entry Unconfirmed','We could not confirm the last cash entry. Check the shop connection, then choose Check Last Cash Entry. Do not enter it again.')

    def refresh_all_data(self):
        emp_id = self.get_current_employee_id()
        self.pill_status.setText("Checking Shift")
        self.pill_status.set_pill_type(BadgePill.TYPE_INFO)
        self.lbl_session_info.setText("Updating drawer totals…")

        def load():
            session = _CASH_CONTROLLER.active_session(emp_id)
            if not session:
                return None, {}, []
            session_id = session["id"]
            return (
                session,
                _CASH_CONTROLLER.cash_summary(session_id) or {},
                _CASH_CONTROLLER.session_movements(session_id, 50),
            )

        self._tasks.run_latest("last-close", lambda: _CASH_CONTROLLER.last_closed_session(emp_id),
                               self._show_last_close,
                               lambda _e: self.lbl_last_close.setText("Last closing summary unavailable. Try again."))
        self._tasks.run_latest(
            "cash-snapshot",
            load,
            self._apply_cash_snapshot,
            lambda _details: self._cash_load_failed(),
        )

    def _show_last_close(self, summary):
        self.lbl_last_close.setText(
            f"Last shift closed: {summary['closed_at']}\n"
            f"Expected: Rs. {summary['expected_cash']:,.2f} • Counted: Rs. {summary['actual_cash']:,.2f} • "
            f"Difference: Rs. {summary['discrepancy']:,.2f}\n{summary['notes']}" if summary else "")

    def _apply_cash_snapshot(self, payload):
        session, summary, rows = payload
        self.active_session = session
        SessionState.get_instance().set_cash_session(session)
        self._current_summary = summary or {}
        if self.active_session:
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
        self.populate_movements_table(rows or [])

    def _cash_load_failed(self):
        self.pill_status.setText("Could Not Check")
        self.pill_status.set_pill_type(BadgePill.TYPE_DANGER)
        self.lbl_session_info.setText("Could not read the current cash shift. Try again.")
        self.tbl_movements.setRowCount(0)

    def populate_movements_table(self, rows=None):
        rows = list(rows or [])
        self.tbl_movements.setUpdatesEnabled(False)
        try:
            self.tbl_movements.setRowCount(len(rows))
            for row, item in enumerate(rows):
                _movement_id, _session_id, movement_type, amount, reason, timestamp = item
                self.tbl_movements.setItem(
                    row,
                    0,
                    QTableWidgetItem(CASH_MOVEMENT_LABELS.get(str(movement_type), str(movement_type))),
                )
                self.tbl_movements.setItem(row, 1, QTableWidgetItem(f"Rs. {float(amount):.2f}"))
                self.tbl_movements.setItem(row, 2, QTableWidgetItem(str(reason)))
                self.tbl_movements.setItem(row, 3, QTableWidgetItem(str(timestamp)))
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
        dialog = RecordMovementDialog(
            self.active_session["id"], self.get_current_employee_id(), self
        )
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def close_current_session(self):
        if not self.active_session:
            return
        expected_cash = float(self._current_summary.get("expected_cash", 0.0))
        dialog = CloseSessionDialog(self.active_session["id"], expected_cash, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()
