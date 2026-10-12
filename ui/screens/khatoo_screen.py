"""
Pharma-Khaato Native PySide6 Customer Credit Screen
Features credit ledger inspection, debt filtering, and payment settlement recording.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox
)
from PySide6.QtCore import Qt

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog

from controllers.khatoo_controller import KhatooController

_KHATOO_CONTROLLER = KhatooController()


class RecordPaymentDialog(QDialog):
    """Modal dialog for recording a customer-credit payment."""

    def __init__(self, khatoo_id: int, cust_name: str, current_due: float, parent=None):
        super().__init__(parent)
        self.khatoo_id = khatoo_id
        self.current_due = current_due

        self.setWindowTitle(f"Record Payment — {cust_name}")
        configure_dialog(self, 480, 330, minimum_width=390, minimum_height=270)
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

        title = QLabel("Record Payment")
        title.setObjectName("h2")
        title.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        lbl_info = QLabel(f"Customer: {cust_name}\nBalance: Rs. {current_due:.2f}")
        lbl_info.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        layout.addWidget(lbl_info)

        layout.addSpacing(6)

        form = QFormLayout()
        self.spn_amount = QDoubleSpinBox()
        self.spn_amount.setRange(0.01, float(current_due))
        self.spn_amount.setValue(float(current_due))
        self.spn_amount.setPrefix("Rs. ")
        self.spn_amount.setDecimals(2)
        self.spn_amount.setAccessibleName("Payment amount")
        form.addRow("Payment amount:", self.spn_amount)

        layout.addLayout(form)
        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        self.btn_confirm = QPushButton("Save Payment")
        self.btn_confirm.setObjectName("primaryButton")
        self.btn_confirm.setStyleSheet(
            f"background-color: {ThemeTokens.ACCENT}; color: #FFFFFF; "
            "padding: 8px 16px; border-radius: 4px; font-weight: 700;"
        )
        self.btn_confirm.clicked.connect(self.on_confirm)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_confirm)
        layout.addLayout(btn_box)

    def on_confirm(self):
        amt = self.spn_amount.value()
        ok, msg = _KHATOO_CONTROLLER.record_payment(self.khatoo_id, amt)
        if ok:
            target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(target, msg, ToastType.SUCCESS)
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
            subtitle="See what customers owe and record full or partial payments."
        )

        self.pill_total_ledger = BadgePill("Open Credits: 0", BadgePill.TYPE_INFO)
        self.pill_total_due = BadgePill("Total Due: Rs. 0.00", BadgePill.TYPE_WARNING)
        header_card.add_pill(self.pill_total_ledger)
        header_card.add_pill(self.pill_total_due)
        layout.addWidget(header_card)

        table_card = Card()
        table_layout = table_card.layout()
        table_layout.setSpacing(12)

        bar_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by customer name or CNIC")
        self.txt_search.setAccessibleName("Search customer credit")
        self.txt_search.textChanged.connect(self.on_search)
        bar_layout.addWidget(self.txt_search)
        table_layout.addLayout(bar_layout)

        # Keep the internal credit reference in column 0 for callbacks, but the
        # shared table-polish helper hides exact database-key columns from users.
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
        self.tbl_ledger.verticalHeader().setVisible(False)
        polish_table(self.tbl_ledger, min_row_height=40)
        self.tbl_ledger.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_ledger.setSelectionBehavior(QTableWidget.SelectRows)

        table_layout.addWidget(self.tbl_ledger, 1)
        layout.addWidget(table_card, 1)

        self.refresh_all_data()

    def refresh_all_data(self):
        records = _KHATOO_CONTROLLER.load("")
        self.populate_ledger_table(records)

        total_due = _KHATOO_CONTROLLER.summary()
        self.pill_total_ledger.setText(f"Open Credits: {len(records)}")
        self.pill_total_due.setText(f"Total Due: Rs. {total_due:.2f}")

    def populate_ledger_table(self, records):
        self.tbl_ledger.setRowCount(len(records))
        for row, item in enumerate(records):
            k_id, cust_name, purchase_id, amount_due, amount_paid, cnic = item

            self.tbl_ledger.setItem(row, 0, QTableWidgetItem(str(k_id)))
            self.tbl_ledger.setItem(row, 1, QTableWidgetItem(str(cust_name)))
            self.tbl_ledger.setItem(row, 2, QTableWidgetItem(f"Sale #{purchase_id}"))
            self.tbl_ledger.setItem(row, 3, QTableWidgetItem(f"Rs. {float(amount_paid):.2f}"))
            self.tbl_ledger.setItem(row, 4, QTableWidgetItem(f"Rs. {float(amount_due):.2f}"))
            self.tbl_ledger.setItem(row, 5, QTableWidgetItem(str(cnic)))

            if float(amount_due) > 0:
                btn_pay = QPushButton("Pay")
                btn_pay.setProperty("compact", True)
                btn_pay.setProperty("accent", True)
                btn_pay.setMinimumWidth(72)
                btn_pay.setMaximumWidth(96)
                btn_pay.setAccessibleName(f"Record payment for {cust_name}")
                btn_pay.clicked.connect(
                    lambda checked=False, kid=k_id, cname=cust_name, due=float(amount_due):
                    self.open_record_payment_dialog(kid, cname, due)
                )
                self.tbl_ledger.setCellWidget(row, 6, btn_pay)
            else:
                lbl_settled = QLabel("Cleared")
                lbl_settled.setAlignment(Qt.AlignCenter)
                lbl_settled.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-weight: 700;")
                self.tbl_ledger.setCellWidget(row, 6, lbl_settled)

    def on_search(self, text):
        records = _KHATOO_CONTROLLER.load(text.strip())
        self.populate_ledger_table(records)

    def open_record_payment_dialog(self, khatoo_id: int, cust_name: str, current_due: float):
        dlg = RecordPaymentDialog(khatoo_id, cust_name, current_due, self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def on_screen_show(self):
        """Auto-refresh customer credit whenever the screen is opened."""
        self.refresh_all_data()
