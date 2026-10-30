"""Responsive, low-latency customer directory and credit summary."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QMessageBox, QFrame,
)
from PySide6.QtCore import QTimer, Qt

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog, flexible_side_panel
from ui.app.async_tasks import AsyncTaskRunner
from controllers.customer_controller import CustomerController

_CUSTOMER_CONTROLLER = CustomerController()


class AddCustomerDialog(QDialog):
    def __init__(self, parent=None, initial_name=""):
        super().__init__(parent)
        self.created_customer_id = None
        self.created_customer_name = None
        self._saving = False
        self._tasks = AsyncTaskRunner(self)
        self.setWindowTitle("Add Customer")
        configure_dialog(self, 500, 390, minimum_width=380, minimum_height=320)
        layout = QVBoxLayout(self)
        title = QLabel("Add Customer")
        title.setObjectName("h2")
        layout.addWidget(title)
        help_label = QLabel("Only a name is needed. Phone, area and CNIC are optional.")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        form = QFormLayout()
        self.txt_name = QLineEdit(str(initial_name or ""))
        self.txt_name.setPlaceholderText("Name or familiar shop name")
        self.txt_name.setMaxLength(100)
        self.txt_name.setAccessibleName("Customer name")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("Optional — 0300 1234567")
        self.txt_city = QLineEdit()
        self.txt_city.setPlaceholderText("Optional area or nearby landmark")
        self.txt_city.setMaxLength(100)
        self.txt_cnic = QLineEdit()
        self.txt_cnic.setPlaceholderText("Optional — 13 digits")
        self.txt_cnic.setMaxLength(20)
        form.addRow("Name *:", self.txt_name)
        form.addRow("Phone:", self.txt_phone)
        form.addRow("Area:", self.txt_city)
        form.addRow("CNIC:", self.txt_cnic)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Add Customer")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.on_save)
        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        layout.addLayout(buttons)
        self.txt_name.setFocus()

    def reject(self):
        if not self._saving:
            super().reject()

    def closeEvent(self, event):
        if self._saving:
            event.ignore()
        else:
            super().closeEvent(event)

    def on_save(self):
        if self._saving:
            return
        name = self.txt_name.text().strip()
        if not name:
            show_toast(self, "Enter the customer name.", ToastType.WARNING)
            self.txt_name.setFocus()
            return
        from ui.app.state.session_state import SessionState
        employee_id = (SessionState.get_instance().current_user or {}).get("id")
        args = (name, self.txt_phone.text().strip(), self.txt_city.text().strip(), self.txt_cnic.text().strip(), employee_id)
        self._saving = True
        self.btn_save.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self._tasks.run(lambda: _CUSTOMER_CONTROLLER.create(*args), self._saved,
                        lambda _details: self._save_failed("The customer could not be saved. Try again."))

    def _saved(self, result):
        ok, message, customer_ref = result
        if not ok:
            self._save_failed(message)
            return
        self._saving = False
        self.created_customer_id = customer_ref
        self.created_customer_name = self.txt_name.text().strip()
        show_toast(self.parent() or self, message, ToastType.SUCCESS)
        self.accept()

    def _save_failed(self, message):
        self._saving = False
        self.btn_save.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.warning(self, "Customer Could Not Be Saved", message)


class CustomerScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._tasks = AsyncTaskRunner(self)
        self._selected_cnic: str | None = None
        self._page = 0
        self._page_size = 120

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = ScreenHeader(
            "Customers",
            "Find customers, add new customers, and view outstanding credit."
        )
        self.pill_total_custs = BadgePill("Customers: 0", BadgePill.TYPE_INFO)
        self.pill_total_debt = BadgePill("Credit Due: Rs. 0.00", BadgePill.TYPE_WARNING)
        header.add_pill(self.pill_total_custs)
        header.add_pill(self.pill_total_debt)
        layout.addWidget(header)

        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        left_card = Card()
        left_layout = left_card.layout()
        left_layout.setSpacing(10)
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search name, phone, area or optional CNIC")
        self.txt_search.setAccessibleName("Search customers")
        self.btn_add_cust = QPushButton("Add Customer")
        self.btn_add_cust.setObjectName("primaryButton")
        self.btn_add_cust.clicked.connect(self.open_add_customer_dialog)
        search_row.addWidget(self.txt_search, 1)
        search_row.addWidget(self.btn_add_cust)
        left_layout.addLayout(search_row)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(160)
        self.search_timer.timeout.connect(self._run_search)
        self.txt_search.textChanged.connect(lambda *_: self.search_timer.start())

        self.tbl_customers = QTableWidget(0, 4)
        self.tbl_customers.setHorizontalHeaderLabels(["Customer", "Phone", "Area", "Amount Due"])
        self.tbl_customers.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_customers)
        self.tbl_customers.verticalHeader().setVisible(False)
        self.tbl_customers.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_customers.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_customers.itemSelectionChanged.connect(self.on_customer_selected)
        left_layout.addWidget(self.tbl_customers, 1)
        pager = QHBoxLayout()
        self.btn_previous = QPushButton("Previous")
        self.btn_next = QPushButton("Next")
        self.btn_previous.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))
        pager.addWidget(self.btn_previous)
        pager.addStretch()
        pager.addWidget(self.btn_next)
        left_layout.addLayout(pager)

        right_card = Card()
        flexible_side_panel(right_card, minimum=280, maximum=410)
        right_layout = right_card.layout()
        right_layout.setSpacing(14)
        title = QLabel("Credit Summary")
        title.setObjectName("h2")
        right_layout.addWidget(title)

        self.lbl_selected_cust = QLabel("Select a customer to view their unpaid balance.")
        self.lbl_selected_cust.setObjectName("caption")
        self.lbl_selected_cust.setWordWrap(True)
        right_layout.addWidget(self.lbl_selected_cust)

        self.lbl_total_cust_debt = QLabel("Total Due: Rs. 0.00")
        self.lbl_total_cust_debt.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        right_layout.addWidget(self.lbl_total_cust_debt)

        aging_hdr = QLabel("How long the balance has been due:")
        aging_hdr.setStyleSheet("font-weight: 600;")
        right_layout.addWidget(aging_hdr)

        aging_box = QFrame()
        aging_box.setObjectName("insetPanel")
        aging_layout = QVBoxLayout(aging_box)
        self.lbl_age_30 = QLabel("0 - 30 Days: Rs. 0.00")
        self.lbl_age_60 = QLabel("31 - 60 Days: Rs. 0.00")
        self.lbl_age_plus = QLabel("61+ Days: Rs. 0.00")
        self.lbl_age_30.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-weight: 600;")
        self.lbl_age_60.setStyleSheet(f"color: {ThemeTokens.WARNING}; font-weight: 600;")
        self.lbl_age_plus.setStyleSheet(f"color: {ThemeTokens.DANGER}; font-weight: 800;")
        aging_layout.addWidget(self.lbl_age_30)
        aging_layout.addWidget(self.lbl_age_60)
        aging_layout.addWidget(self.lbl_age_plus)
        right_layout.addWidget(aging_box)
        right_layout.addStretch()

        main_row.addWidget(left_card, 7)
        main_row.addWidget(right_card, 3)
        layout.addLayout(main_row, 1)
        self.refresh_all_data()

    def _change_page(self, delta):
        self._page = max(0, self._page + delta)
        self._load_rows(self.txt_search.text())

    def _load_rows(self, text=""):
        term = text.strip()
        offset = self._page * self._page_size
        self.pill_total_custs.setText("Loading customers…")

        def complete(payload):
            if self.txt_search.text().strip() != term:
                return
            rows, total = payload
            self._selected_cnic = None
            self.populate_customers_table(rows)
            first = offset + 1 if rows else 0
            self.pill_total_custs.setText(f"Customers: {first}–{offset + len(rows)} of {total}")
            self.btn_previous.setEnabled(offset > 0)
            self.btn_next.setEnabled(offset + len(rows) < total)

        self._tasks.run_latest(
            "customer-list",
            lambda: (_CUSTOMER_CONTROLLER.search_with_debt(term, self._page_size, offset), _CUSTOMER_CONTROLLER.count(term)),
            complete,
            lambda _message: self._customer_load_failed(),
        )

    def _refresh_total_credit(self):
        self._tasks.run_latest(
            "customer-credit-total",
            _CUSTOMER_CONTROLLER.khatoo_summary,
            lambda total: self.pill_total_debt.setText(f"Credit Due: Rs. {float(total):.2f}"),
            lambda _message: self.pill_total_debt.setText("Credit Due: unavailable"),
        )

    def refresh_all_data(self):
        self._load_rows(self.txt_search.text() if hasattr(self, "txt_search") else "")
        self._refresh_total_credit()

    def populate_customers_table(self, customers):
        self.tbl_customers.blockSignals(True)
        self.tbl_customers.setUpdatesEnabled(False)
        try:
            self.tbl_customers.setRowCount(len(customers))
            for row, item in enumerate(customers):
                cnic, fname, lname, phone, city, debt = item
                full_name = " ".join(part for part in (str(fname).strip(), str(lname).strip()) if part)
                name_item = QTableWidgetItem(full_name or "Unnamed customer")
                name_item.setData(Qt.ItemDataRole.UserRole, cnic)
                self.tbl_customers.setItem(row, 0, name_item)
                self.tbl_customers.setItem(row, 1, QTableWidgetItem(str(phone or "—")))
                self.tbl_customers.setItem(row, 2, QTableWidgetItem(str(city)))
                self.tbl_customers.setItem(row, 3, QTableWidgetItem(f"Rs. {float(debt):.2f}"))
        finally:
            self.tbl_customers.setUpdatesEnabled(True)
            self.tbl_customers.blockSignals(False)

    def _customer_load_failed(self):
        self.pill_total_custs.setText("Customers: unavailable")
        if self.show_message_box:
            show_toast(self, "Could not load customers. Try again.", ToastType.WARNING)

    def _run_search(self):
        self._page = 0
        self._load_rows(self.txt_search.text())

    def on_search(self, text):
        self.search_timer.start()

    def on_customer_selected(self):
        rows = self.tbl_customers.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        name_item = self.tbl_customers.item(row, 0)
        cnic_item = self.tbl_customers.item(row, 1)
        if not name_item or not cnic_item:
            return
        customer_name = name_item.text()
        cnic = name_item.data(Qt.ItemDataRole.UserRole)
        self._selected_cnic = cnic
        self.lbl_selected_cust.setText(customer_name)
        self.lbl_total_cust_debt.setText("Total Due: …")
        self.lbl_age_30.setText("0 - 30 Days: …")
        self.lbl_age_60.setText("31 - 60 Days: …")
        self.lbl_age_plus.setText("61+ Days: …")

        def load_detail():
            return (
                cnic,
                _CUSTOMER_CONTROLLER.total_debt(cnic),
                _CUSTOMER_CONTROLLER.debt_aging(cnic),
            )

        self._tasks.run_latest(
            "customer-detail",
            load_detail,
            self._apply_customer_detail,
            lambda _message: self._customer_detail_failed(cnic),
        )

    def _apply_customer_detail(self, payload):
        cnic, debt, aging = payload
        if cnic != self._selected_cnic:
            return
        self.lbl_total_cust_debt.setText(f"Total Due: Rs. {float(debt):.2f}")
        self.lbl_age_30.setText(f"0 - 30 Days: Rs. {aging['0_30']:.2f}")
        self.lbl_age_60.setText(f"31 - 60 Days: Rs. {aging['31_60']:.2f}")
        self.lbl_age_plus.setText(f"61+ Days: Rs. {aging['61_plus']:.2f}")

    def _customer_detail_failed(self, cnic: str):
        if cnic != self._selected_cnic:
            return
        self.lbl_total_cust_debt.setText("Total Due: unavailable")
        self.lbl_age_30.setText("0 - 30 Days: unavailable")
        self.lbl_age_60.setText("31 - 60 Days: unavailable")
        self.lbl_age_plus.setText("61+ Days: unavailable")

    def open_add_customer_dialog(self):
        dlg = AddCustomerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def on_screen_show(self):
        self.refresh_all_data()
