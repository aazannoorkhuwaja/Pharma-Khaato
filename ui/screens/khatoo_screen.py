from ui.widgets.semantic_style import set_tone
"""Customer-credit ledger and repayment workflow."""

import uuid

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QMessageBox, QPlainTextEdit, QInputDialog,
)
from PySide6.QtCore import Qt, QTimer

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog
from ui.app.async_tasks import AsyncTaskRunner
from ui.app.state.session_state import SessionState
from controllers.khatoo_controller import KhatooController

_KHATOO_CONTROLLER = KhatooController()


class RecordPaymentDialog(QDialog):
    """Record a repayment without blocking the dialog on database writes."""

    def __init__(self, khatoo_id: int, cust_name: str, current_due: float, parent=None, draft=None):
        super().__init__(parent)
        self.khatoo_id = khatoo_id
        self.operation_id = uuid.uuid4().hex
        self.saved_operation_id = None
        self.current_due = current_due
        self.cust_name = cust_name
        self._draft = draft
        self._tasks = AsyncTaskRunner(self)
        self._saving = False
        self.setWindowTitle(f"Record Payment — {cust_name}")
        configure_dialog(self, 500, 410, minimum_width=400, minimum_height=330)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Record Credit Payment")
        title.setObjectName("h2")
        layout.addWidget(title)

        info = QLabel(f"Customer: {cust_name}\nBalance: Rs. {current_due:.2f}")
        info.setWordWrap(True)
        set_tone(info, "secondary")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        self.spn_amount = QDoubleSpinBox()
        self.spn_amount.setRange(0.01, float(current_due))
        self.spn_amount.setValue(float(current_due))
        self.spn_amount.setPrefix("Rs. ")
        self.spn_amount.setDecimals(2)
        self.spn_amount.setAccessibleName("Credit payment amount")
        form.addRow("Amount:", self.spn_amount)

        self.cmb_method = QComboBox()
        self.cmb_method.addItem("Cash", "Cash")
        self.cmb_method.addItem("Card", "Credit Card")
        self.cmb_method.addItem("Easypaisa", "Easypaisa")
        self.cmb_method.addItem("JazzCash", "JazzCash")
        self.cmb_method.addItem("Bank Transfer", "Bank Transfer")
        self.cmb_method.addItem("Raast", "Raast")
        self.cmb_method.setAccessibleName("Credit payment method")
        self.cmb_method.currentIndexChanged.connect(self._update_cash_help)
        form.addRow("Paid with:", self.cmb_method)

        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("Optional note or transfer reference")
        self.txt_note.setMaxLength(250)
        form.addRow("Note:", self.txt_note)
        layout.addLayout(form)

        self.lbl_cash_help = QLabel()
        self.lbl_cash_help.setWordWrap(True)
        self.lbl_cash_help.setObjectName("caption")
        layout.addWidget(self.lbl_cash_help)
        self._update_cash_help()

        buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_confirm = QPushButton("Save Payment")
        self.btn_confirm.setObjectName("primaryButton")
        self.btn_confirm.clicked.connect(self.on_confirm)
        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_confirm)
        layout.addLayout(buttons)
        if draft:
            self.operation_id = draft["operation_id"]
            self.spn_amount.setValue(float(draft["amount"]))
            self.cmb_method.setCurrentIndex(self.cmb_method.findData(draft["payment_method"]))
            self.txt_note.setText(draft["note"])
            self.spn_amount.setEnabled(False)
            self.cmb_method.setEnabled(False)
            self.txt_note.setEnabled(False)
            self.btn_confirm.setText("Confirm Previous Payment")
            self.lbl_cash_help.setText("This restores a previous payment request. Confirming checks its saved reference and cannot record it twice.")

    def reject(self):
        if not self._saving:
            super().reject()

    def closeEvent(self, event):
        if self._saving:
            event.ignore()
        else:
            super().closeEvent(event)

    def _current_employee_id(self):
        user = SessionState.get_instance().current_user or {}
        return user.get("id")

    def _update_cash_help(self, *_):
        if self.cmb_method.currentData() == "Cash":
            self.lbl_cash_help.setText(
                "Cash repayments are added to the current cash shift automatically."
            )
            self.lbl_cash_help.setStyleSheet(f"color: {ThemeTokens.WARNING};")
        else:
            self.lbl_cash_help.setText(
                "Digital repayments are recorded separately and do not change drawer cash."
            )
            set_tone(self.lbl_cash_help, "muted")

    def on_confirm(self):
        if self._saving:
            return
        employee_id = self._current_employee_id()
        if employee_id is None:
            QMessageBox.critical(self, "Sign In Required", "Sign in again before recording a payment.")
            return

        args = (
            self.khatoo_id,
            self.spn_amount.value(),
            employee_id,
            self.cmb_method.currentData() or self.cmb_method.currentText(),
            self.txt_note.text().strip(),
            self.operation_id,
        )
        self._saving = True
        self.btn_confirm.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_confirm.setText("Saving…")
        self.spn_amount.setEnabled(False)
        self.cmb_method.setEnabled(False)
        self.txt_note.setEnabled(False)
        payload = self._draft or {
            "customer_ref": self.khatoo_id, "amount": self.spn_amount.value(), "employee_id": employee_id,
            "payment_method": self.cmb_method.currentData(), "note": self.txt_note.text().strip(),
            "operation_id": self.operation_id, "customer_name": self.cust_name, "current_due": self.current_due,
        }
        self._draft = payload

        def save():
            _KHATOO_CONTROLLER.save_pending_payment(payload)
            result = _KHATOO_CONTROLLER.collect(payload["customer_ref"], payload["amount"], payload["employee_id"],
                    payload["payment_method"], payload["note"], payload["operation_id"])
            details = result[2] or {}
            if result[0] or details.get("outcome") == "not_recorded":
                _KHATOO_CONTROLLER.clear_pending_payment(employee_id, self.operation_id)
            return result

        self._tasks.run(save, self._payment_saved, lambda _details: self._payment_failed())

    def _payment_saved(self, result):
        self._saving = False
        ok, msg = result[:2]
        if ok:
            self.saved_operation_id = self.operation_id
            show_toast(self.parent() or self, msg, ToastType.SUCCESS)
            self.accept()
            return
        if len(result) > 2 and (result[2] or {}).get("outcome") == "not_recorded":
            self._draft = None
            self.spn_amount.setEnabled(True)
            self.cmb_method.setEnabled(True)
            self.txt_note.setEnabled(True)
        self.btn_confirm.setText("Save Payment")
        self.btn_confirm.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Payment Could Not Be Saved", msg)

    def _payment_failed(self):
        self._saving = False
        self.btn_confirm.setText("Save Payment")
        self.btn_confirm.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(
            self,
            "Payment Could Not Be Saved",
            "The payment outcome is unconfirmed. Retry this form with the same details before starting another payment.",
        )


class KhatooScreen(QWidget):
    """Lightweight credit list with worker-backed reads."""

    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._tasks = AsyncTaskRunner(self)
        self._page = 0
        self._page_size = 100

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            title="Customer Credit",
            subtitle="Receive one payment across unpaid bills, print statements, and review payment history."
        )
        self.pill_total_ledger = BadgePill("Open Credits: …", BadgePill.TYPE_INFO)
        self.pill_total_due = BadgePill("Total Due: …", BadgePill.TYPE_WARNING)
        header_card.add_pill(self.pill_total_ledger)
        header_card.add_pill(self.pill_total_due)
        layout.addWidget(header_card)

        table_card = Card()
        table_layout = table_card.layout()
        table_layout.setSpacing(12)

        tools = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search name, phone, area or optional CNIC")
        self.txt_search.setAccessibleName("Search customer credit")
        tools.addWidget(self.txt_search, 1)

        self.btn_record_payment = QPushButton("Record Payment")
        self.btn_record_payment.setObjectName("primaryButton")
        self.btn_record_payment.setEnabled(False)
        self.btn_record_payment.setToolTip("Select a customer balance first")
        self.btn_record_payment.clicked.connect(self.open_selected_payment)
        tools.addWidget(self.btn_record_payment)
        self.btn_statement = QPushButton("Statement")
        self.btn_statement.clicked.connect(self.open_statement)
        tools.addWidget(self.btn_statement)
        self.btn_history = QPushButton("Payment History")
        self.btn_history.clicked.connect(self.open_history)
        tools.addWidget(self.btn_history)
        table_layout.addLayout(tools)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(160)
        self.search_timer.timeout.connect(self._run_search)
        self.txt_search.textChanged.connect(self._queue_search)

        self.tbl_ledger = QTableWidget(0, 5)
        self.tbl_ledger.setHorizontalHeaderLabels(
            ["Customer", "Phone", "Area", "Unpaid Bills", "Balance"]
        )
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        polish_table(self.tbl_ledger, min_row_height=38)
        self.tbl_ledger.verticalHeader().setVisible(False)
        self.tbl_ledger.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_ledger.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_ledger.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_ledger.itemSelectionChanged.connect(self._update_payment_action)
        self.tbl_ledger.doubleClicked.connect(lambda *_: self.open_selected_payment())
        table_layout.addWidget(self.tbl_ledger, 1)
        pager = QHBoxLayout()
        self.btn_previous = QPushButton("Previous")
        self.btn_next = QPushButton("Next")
        self.btn_previous.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))
        pager.addWidget(self.btn_previous)
        pager.addStretch()
        pager.addWidget(self.btn_next)
        table_layout.addLayout(pager)
        layout.addWidget(table_card, 1)

        self.lbl_empty = QLabel()
        self.lbl_empty.setWordWrap(True)
        layout.addWidget(self.lbl_empty)
        self.refresh_all_data()

    def refresh_all_data(self):
        term = self.txt_search.text().strip() if hasattr(self, "txt_search") else ""
        self.pill_total_ledger.setText("Open Credits: …")
        self.pill_total_due.setText("Total Due: …")

        def load():
            return (_KHATOO_CONTROLLER.accounts(term, self._page_size, self._page * self._page_size),
                    _KHATOO_CONTROLLER.summary(), _KHATOO_CONTROLLER.account_count(term))

        self._tasks.run_latest(
            "credit-snapshot",
            load,
            self._apply_credit_snapshot,
            lambda _details: self._credit_load_failed(),
        )

    def _apply_credit_snapshot(self, payload):
        records, total_due, total_count = payload
        records = list(records or [])
        self.lbl_empty.setText(
            "No customers match this search. Try a different name or phone."
            if not records and self.txt_search.text().strip() else
            "No customer credit accounts yet. A sale paid with Customer Credit appears here; record repayments here when the customer pays."
            if not records else "")
        self.populate_ledger_table(records)
        offset = self._page * self._page_size
        first = offset + 1 if records else 0
        self.pill_total_ledger.setText(f"Accounts: {first}–{offset + len(records)} of {total_count}")
        self.btn_previous.setEnabled(offset > 0)
        self.btn_next.setEnabled(offset + len(records) < total_count)
        self.pill_total_due.setText(f"Total Due: Rs. {float(total_due):.2f}")

    def _credit_load_failed(self):
        self.lbl_empty.setText("Could not load customer credit. Check the connection and refresh this screen.")
        self.pill_total_ledger.setText("Open Credits: unavailable")
        self.pill_total_due.setText("Total Due: unavailable")
        if self.show_message_box:
            show_toast(self, "Could not load customer credit. Try again.", ToastType.WARNING)

    def populate_ledger_table(self, records):
        self.tbl_ledger.blockSignals(True)
        self.tbl_ledger.setUpdatesEnabled(False)
        try:
            self.tbl_ledger.clearContents()
            self.tbl_ledger.setRowCount(len(records))
            for row, item in enumerate(records):
                customer_ref, cust_name, phone, area, amount_due, bill_count = item

                customer_item = QTableWidgetItem(str(cust_name))
                customer_item.setData(Qt.ItemDataRole.UserRole, str(customer_ref))
                customer_item.setData(Qt.ItemDataRole.UserRole + 1, float(amount_due))
                self.tbl_ledger.setItem(row, 0, customer_item)
                self.tbl_ledger.setItem(row, 1, QTableWidgetItem(str(phone or "—")))
                self.tbl_ledger.setItem(row, 2, QTableWidgetItem(str(area or "—")))
                self.tbl_ledger.setItem(row, 3, QTableWidgetItem(str(bill_count)))
                self.tbl_ledger.setItem(row, 4, QTableWidgetItem(f"Rs. {float(amount_due):.2f}"))
        finally:
            self.tbl_ledger.setUpdatesEnabled(True)
            self.tbl_ledger.blockSignals(False)
        self._update_payment_action()

    def _selected_payment_context(self):
        selected = self.tbl_ledger.selectionModel().selectedRows()
        if not selected:
            return None
        row = selected[0].row()
        customer_item = self.tbl_ledger.item(row, 0)
        if customer_item is None:
            return None
        try:
            return (
                str(customer_item.data(Qt.ItemDataRole.UserRole)),
                customer_item.text(),
                float(customer_item.data(Qt.ItemDataRole.UserRole + 1)),
            )
        except (TypeError, ValueError):
            return None

    def _update_payment_action(self):
        context = self._selected_payment_context()
        enabled = context is not None
        self.btn_record_payment.setEnabled(enabled)
        self.btn_statement.setEnabled(enabled)
        self.btn_record_payment.setToolTip(
            "Record a full or partial repayment for the selected balance"
            if enabled
            else "Select a customer balance first"
        )

    def open_selected_payment(self):
        context = self._selected_payment_context()
        if context is None:
            show_toast(self, "Select a customer balance first.", ToastType.INFO)
            return
        self.open_record_payment_dialog(*context)

    def _queue_search(self, *_):
        self.search_timer.start()

    def _change_page(self, delta):
        self._page = max(0, self._page + delta)
        self.refresh_all_data()

    def _run_search(self):
        self._page = 0
        self.refresh_all_data()

    def open_statement(self):
        context = self._selected_payment_context()
        if not context:
            return
        self._tasks.run(lambda: _KHATOO_CONTROLLER.statement(context[0]),
                        lambda text: CreditTextDialog("Customer Statement", text, self).exec(),
                        lambda _details: show_toast(self, "Statement unavailable. Try again.", ToastType.WARNING))

    def open_history(self):
        CreditHistoryDialog(self).exec()
        self.refresh_all_data()

    def on_search(self, text):
        self._queue_search(text)

    def open_record_payment_dialog(self, khatoo_id, cust_name, current_due):
        employee_id = (SessionState.get_instance().current_user or {}).get("id")
        if employee_id is None:
            return

        def open_dialog(draft):
            ref = draft["customer_ref"] if draft else khatoo_id
            name = draft["customer_name"] if draft else cust_name
            due = draft["current_due"] if draft else current_due
            dlg = RecordPaymentDialog(ref, name, due, self, draft=draft)
            if dlg.exec() == QDialog.Accepted:
                self.refresh_all_data()

        self._tasks.run(lambda: _KHATOO_CONTROLLER.load_pending_payment(employee_id), open_dialog,
                        lambda _details: QMessageBox.warning(self, "Payment Recovery", "A previous payment could not be read. Ask the owner to review payment history before accepting another payment."))

    def on_screen_show(self):
        self.refresh_all_data()


class CreditTextDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self._tasks = AsyncTaskRunner(self)
        self.setWindowTitle(title)
        configure_dialog(self, 600, 620, minimum_width=380, minimum_height=350)
        layout = QVBoxLayout(self)
        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QHBoxLayout()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        self.btn_print = QPushButton("Print")
        self.btn_print.setObjectName("primaryButton")
        self.btn_print.clicked.connect(lambda: self._print(text))
        buttons.addStretch()
        buttons.addWidget(close)
        buttons.addWidget(self.btn_print)
        layout.addLayout(buttons)

    def _print(self, text):
        self.btn_print.setEnabled(False)
        self._tasks.run(lambda: _KHATOO_CONTROLLER.print_text(text), self._printed,
                        lambda _details: self._printed(False))

    def _printed(self, ok):
        self.btn_print.setEnabled(True)
        if ok:
            show_toast(self, "Sent to the printer.", ToastType.SUCCESS)
        else:
            QMessageBox.warning(self, "Printer Unavailable", "The payment is saved. Check the printer and try printing again.")


class CreditHistoryDialog(QDialog):
    """Include settled accounts and page explicitly through the whole history."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = AsyncTaskRunner(self)
        self._page = 0
        self._size = 100
        self._records = []
        self._saving = False
        self._correction_id = None
        self.setWindowTitle("Customer Payment History")
        configure_dialog(self, 950, 620, minimum_width=600, minimum_height=380)
        layout = QVBoxLayout(self)
        self.lbl_count = QLabel("Loading history…")
        layout.addWidget(self.lbl_count)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Date", "Customer", "Received", "Method", "Staff", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        polish_table(self.table)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.doubleClicked.connect(lambda *_: self._receipt())
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        self.btn_slip = QPushButton("Payment Slip")
        self.btn_statement = QPushButton("Customer Statement")
        self.btn_reverse = QPushButton("Owner: Correct Payment")
        self.btn_slip.clicked.connect(self._receipt)
        self.btn_statement.clicked.connect(self._statement)
        self.btn_reverse.clicked.connect(self._reverse)
        actions.addWidget(self.btn_slip)
        actions.addWidget(self.btn_statement)
        actions.addStretch()
        actions.addWidget(self.btn_reverse)
        layout.addLayout(actions)
        pager = QHBoxLayout()
        self.btn_previous = QPushButton("Previous")
        self.btn_next = QPushButton("Next")
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        self.btn_previous.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))
        pager.addWidget(self.btn_previous)
        pager.addWidget(self.btn_next)
        pager.addStretch()
        pager.addWidget(self.btn_close)
        layout.addLayout(pager)
        self._load()

    def reject(self):
        if not self._saving:
            super().reject()

    def closeEvent(self, event):
        if self._saving:
            event.ignore()
        else:
            super().closeEvent(event)

    def _change_page(self, delta):
        self._page = max(0, self._page + delta)
        self._load()

    def _load(self):
        self._tasks.run_latest("credit-history", lambda: (
            _KHATOO_CONTROLLER.payment_history(self._size, None, self._page * self._size),
            _KHATOO_CONTROLLER.payment_count()), self._loaded, lambda _details: self._load_failed())

    def _loaded(self, payload):
        self._records, total = payload
        self.table.setRowCount(len(self._records))
        for row, record in enumerate(self._records):
            payment_id, ledger, amount, method, when, staff, note, name, operation_id, reversal_id, ref = record
            values = [when, name, f"Rs. {float(amount):.2f}", method, staff, "Corrected" if reversal_id else "Received"]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        offset = self._page * self._size
        first = offset + 1 if self._records else 0
        self.lbl_count.setText(f"Payments: {first}–{offset + len(self._records)} of {total}")
        self.btn_previous.setEnabled(offset > 0)
        self.btn_next.setEnabled(offset + len(self._records) < total)
        self._selection_changed()

    def _load_failed(self):
        self.lbl_count.setText("Payment history unavailable. Close and try again.")
        self._records = []
        self.table.setRowCount(0)
        self._selection_changed()

    def _selected(self):
        row = self.table.currentRow()
        return self._records[row] if 0 <= row < len(self._records) else None

    def _selection_changed(self):
        record = self._selected()
        self.btn_slip.setEnabled(bool(record and record[8]) and not self._saving)
        self.btn_statement.setEnabled(bool(record) and not self._saving)
        self.btn_reverse.setEnabled(bool(record and not record[9]) and not self._saving)

    def _receipt(self):
        record = self._selected()
        if not record or not record[8]:
            return
        self._tasks.run(lambda: _KHATOO_CONTROLLER.receipt(record[8]),
                        lambda text: CreditTextDialog("Payment Receipt", text, self).exec(),
                        lambda _details: show_toast(self, "Payment slip unavailable. Try again.", ToastType.WARNING))

    def _statement(self):
        record = self._selected()
        if not record:
            return
        self._tasks.run(lambda: _KHATOO_CONTROLLER.statement(record[10]),
                        lambda text: CreditTextDialog("Customer Statement", text, self).exec(),
                        lambda _details: show_toast(self, "Statement unavailable. Try again.", ToastType.WARNING))

    def _reverse(self):
        record = self._selected()
        employee_id = (SessionState.get_instance().current_user or {}).get("id")
        if not record or employee_id is None:
            return
        reason, accepted = QInputDialog.getText(self, "Correct Customer Payment",
            f"{record[7]} — Rs. {float(record[2]):.2f}\nThis restores the debt and records the money returned.\nAn owner or manager must be signed in. Reason:")
        if not accepted or not reason.strip():
            return
        self._correction_id = self._correction_id or uuid.uuid4().hex
        self._saving = True
        self.btn_close.setEnabled(False)
        self._selection_changed()
        self._tasks.run(lambda: _KHATOO_CONTROLLER.reverse(record[0], employee_id, reason, self._correction_id),
                        self._reversed, lambda _details: self._reverse_failed())

    def _reversed(self, result):
        self._saving = False
        self.btn_close.setEnabled(True)
        ok, message, _details = result
        if ok:
            self._correction_id = None
            show_toast(self, message, ToastType.SUCCESS)
        else:
            QMessageBox.warning(self, "Payment Correction", message)
        self._load()

    def _reverse_failed(self):
        self._saving = False
        self.btn_close.setEnabled(True)
        QMessageBox.warning(self, "Correction Unconfirmed", "Check payment history before trying the correction again.")
        self._load()
