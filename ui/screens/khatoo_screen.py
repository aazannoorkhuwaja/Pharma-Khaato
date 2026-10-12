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
    """Lightweight credit list: one action button, not one QWidget per row."""

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

        tools = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by customer name or CNIC")
        self.txt_search.setAccessibleName("Search customer credit")
        tools.addWidget(self.txt_search, 1)

        self.btn_record_payment = QPushButton("Record Payment")
        self.btn_record_payment.setObjectName("primaryButton")
        self.btn_record_payment.setEnabled(False)
        self.btn_record_payment.setToolTip("Select a customer balance first")
        self.btn_record_payment.clicked.connect(self.open_selected_payment)
        tools.addWidget(self.btn_record_payment)
        table_layout.addLayout(tools)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(160)
        self.search_timer.timeout.connect(self._run_search)
        self.txt_search.textChanged.connect(self._queue_search)

        # Internal ledger IDs stay in Qt.UserRole instead of becoming visible
        # columns. Avoiding hundreds of per-row QPushButtons also cuts creation,
        # style, layout, and repaint overhead substantially on large ledgers.
        self.tbl_ledger = QTableWidget(0, 5)
        self.tbl_ledger.setHorizontalHeaderLabels(
            ["Customer", "Sale", "Paid", "Balance", "CNIC"]
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
        layout.addWidget(table_card, 1)

        self.refresh_all_data()

    def refresh_all_data(self):
        records = _KHATOO_CONTROLLER.load(
            self.txt_search.text().strip() if hasattr(self, "txt_search") else ""
        )
        self.populate_ledger_table(records)
        self.pill_total_ledger.setText(f"Open Credits: {len(records)}")
        self.pill_total_due.setText(f"Total Due: Rs. {_KHATOO_CONTROLLER.summary():.2f}")

    def populate_ledger_table(self, records):
        self.tbl_ledger.setUpdatesEnabled(False)
        try:
            self.tbl_ledger.clearContents()
            self.tbl_ledger.setRowCount(len(records))
            for row, item in enumerate(records):
                k_id, cust_name, purchase_id, amount_due, amount_paid, cnic = item

                customer_item = QTableWidgetItem(str(cust_name))
                customer_item.setData(Qt.ItemDataRole.UserRole, int(k_id))
                customer_item.setData(Qt.ItemDataRole.UserRole + 1, float(amount_due))
                self.tbl_ledger.setItem(row, 0, customer_item)
                self.tbl_ledger.setItem(row, 1, QTableWidgetItem(f"Sale #{purchase_id}"))
                self.tbl_ledger.setItem(row, 2, QTableWidgetItem(f"Rs. {float(amount_paid):.2f}"))
                self.tbl_ledger.setItem(row, 3, QTableWidgetItem(f"Rs. {float(amount_due):.2f}"))
                self.tbl_ledger.setItem(row, 4, QTableWidgetItem(str(cnic)))
        finally:
            self.tbl_ledger.setUpdatesEnabled(True)
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
                int(customer_item.data(Qt.ItemDataRole.UserRole)),
                customer_item.text(),
                float(customer_item.data(Qt.ItemDataRole.UserRole + 1)),
            )
        except (TypeError, ValueError):
            return None

    def _update_payment_action(self):
        context = self._selected_payment_context()
        enabled = context is not None
        self.btn_record_payment.setEnabled(enabled)
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
