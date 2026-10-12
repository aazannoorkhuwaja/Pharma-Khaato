"""Customer-credit ledger and repayment workflow."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog
from ui.app.state.session_state import SessionState
from controllers.khatoo_controller import KhatooController

_KHATOO_CONTROLLER = KhatooController()


class RecordPaymentDialog(QDialog):
    """Record a repayment with its real tender and signed-in staff context."""

    def __init__(self, khatoo_id: int, cust_name: str, current_due: float, parent=None):
        super().__init__(parent)
        self.khatoo_id = khatoo_id
        self.current_due = current_due
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
        info.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
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
        self.cmb_method.setAccessibleName("Credit payment method")
        self.cmb_method.currentIndexChanged.connect(self._update_cash_help)
        form.addRow("Paid with:", self.cmb_method)

        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("Optional note")
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
            self.lbl_cash_help.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")

    def on_confirm(self):
        employee_id = self._current_employee_id()
        if employee_id is None:
            QMessageBox.critical(self, "Sign In Required", "Sign in again before recording a payment.")
            return
        ok, msg = _KHATOO_CONTROLLER.record_payment(
            self.khatoo_id,
            self.spn_amount.value(),
            employee_id,
            self.cmb_method.currentData() or self.cmb_method.currentText(),
            self.txt_note.text().strip(),
        )
        if ok:
            show_toast(self.parent() or self, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Payment Could Not Be Saved", msg)


class KhatooScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            title="Customer Credit",
            subtitle="See open balances and record full or partial repayments."
        )
        self.pill_total_ledger = BadgePill("Open Credits: 0", BadgePill.TYPE_INFO)
        self.pill_total_due = BadgePill("Total Due: Rs. 0.00", BadgePill.TYPE_WARNING)
        header_card.add_pill(self.pill_total_ledger)
        header_card.add_pill(self.pill_total_due)
        layout.addWidget(header_card)

        table_card = Card()
        table_layout = table_card.layout()
        table_layout.setSpacing(12)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by customer name or CNIC")
        self.txt_search.setAccessibleName("Search customer credit")
        table_layout.addWidget(self.txt_search)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(160)
        self.search_timer.timeout.connect(self._run_search)
        self.txt_search.textChanged.connect(self._queue_search)

        self.tbl_ledger = QTableWidget(0, 7)
        self.tbl_ledger.setHorizontalHeaderLabels(
            ["Ref #", "Customer", "Sale", "Paid", "Balance", "CNIC", "Payment"]
        )
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        polish_table(self.tbl_ledger, min_row_height=40)
        self.tbl_ledger.verticalHeader().setVisible(False)
        self.tbl_ledger.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_ledger.setSelectionBehavior(QTableWidget.SelectRows)
        table_layout.addWidget(self.tbl_ledger, 1)
        layout.addWidget(table_card, 1)

        self.refresh_all_data()

    def refresh_all_data(self):
        records = _KHATOO_CONTROLLER.load(self.txt_search.text().strip() if hasattr(self, "txt_search") else "")
        self.populate_ledger_table(records)
        self.pill_total_ledger.setText(f"Open Credits: {len(records)}")
        self.pill_total_due.setText(f"Total Due: Rs. {_KHATOO_CONTROLLER.summary():.2f}")

    def populate_ledger_table(self, records):
        self.tbl_ledger.setUpdatesEnabled(False)
        try:
            self.tbl_ledger.setRowCount(len(records))
            for row, item in enumerate(records):
                k_id, cust_name, purchase_id, amount_due, amount_paid, cnic = item
                self.tbl_ledger.setItem(row, 0, QTableWidgetItem(str(k_id)))
                self.tbl_ledger.setItem(row, 1, QTableWidgetItem(str(cust_name)))
                self.tbl_ledger.setItem(row, 2, QTableWidgetItem(f"Sale #{purchase_id}"))
                self.tbl_ledger.setItem(row, 3, QTableWidgetItem(f"Rs. {float(amount_paid):.2f}"))
                self.tbl_ledger.setItem(row, 4, QTableWidgetItem(f"Rs. {float(amount_due):.2f}"))
                self.tbl_ledger.setItem(row, 5, QTableWidgetItem(str(cnic)))

                btn_pay = QPushButton("Pay")
                btn_pay.setProperty("compact", True)
                btn_pay.setProperty("accent", True)
                btn_pay.setMaximumWidth(96)
                btn_pay.setAccessibleName(f"Record payment for {cust_name}")
                btn_pay.clicked.connect(
                    lambda checked=False, kid=k_id, cname=cust_name, due=float(amount_due):
                    self.open_record_payment_dialog(kid, cname, due)
                )
                self.tbl_ledger.setCellWidget(row, 6, btn_pay)
        finally:
            self.tbl_ledger.setUpdatesEnabled(True)

    def _queue_search(self, *_):
        self.search_timer.start()

    def _run_search(self):
        records = _KHATOO_CONTROLLER.load(self.txt_search.text().strip())
        self.populate_ledger_table(records)
        self.pill_total_ledger.setText(f"Open Credits: {len(records)}")

    def on_search(self, text):
        self._queue_search(text)

    def open_record_payment_dialog(self, khatoo_id: int, cust_name: str, current_due: float):
        dlg = RecordPaymentDialog(khatoo_id, cust_name, current_due, self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def on_screen_show(self):
        self.refresh_all_data()
