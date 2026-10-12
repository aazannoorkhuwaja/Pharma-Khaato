"""
Pharma-Khaato Native PySide6 Customer Management Screen
Features customer registration modal, CNIC validation, debt lookup, and debt aging breakdown.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import Toast, ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog, flexible_side_panel

from controllers.customer_controller import CustomerController

_CUSTOMER_CONTROLLER = CustomerController()

class AddCustomerDialog(QDialog):
    """Modal dialog for registering a new customer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Customer")
        configure_dialog(self, 520, 460, minimum_width=400, minimum_height=340)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
            QLabel {{ font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; }}
            QLineEdit {{
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

        title = QLabel("Add Customer")
        title.setStyleSheet(f" font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_cnic = QLineEdit()
        self.txt_cnic.setPlaceholderText("13-digit CNIC, with or without dashes")
        form.addRow("CNIC *:", self.txt_cnic)

        self.txt_fname = QLineEdit()
        self.txt_fname.setPlaceholderText("First Name")
        form.addRow("First Name *:", self.txt_fname)

        self.txt_lname = QLineEdit()
        self.txt_lname.setPlaceholderText("Last Name")
        form.addRow("Last Name *:", self.txt_lname)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Email (optional)")
        form.addRow("Email:", self.txt_email)

        self.txt_city = QLineEdit()
        self.txt_city.setPlaceholderText("City / Area")
        form.addRow("City:", self.txt_city)

        layout.addLayout(form)
        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Add Customer")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setStyleSheet(f"background-color: {ThemeTokens.ACCENT}; color: #FFFFFF; padding: 8px 16px; border-radius: 4px; font-weight: 700;")
        self.btn_save.clicked.connect(self.on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def on_save(self):
        cnic = self.txt_cnic.text().strip()
        fname = self.txt_fname.text().strip()
        lname = self.txt_lname.text().strip()
        email = self.txt_email.text().strip() or "N/A"
        city = self.txt_city.text().strip() or "N/A"

        if not _CUSTOMER_CONTROLLER.validate_cnic(cnic):
            show_toast(self, "Enter a valid 13-digit CNIC.", ToastType.WARNING)
            return

        if not fname or not lname:
            show_toast(self, "Enter the customer’s first and last name.", ToastType.WARNING)
            return

        ok, msg = _CUSTOMER_CONTROLLER.register(cnic, fname, lname, email, city)
        if ok:
            target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(target, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Save Customer", msg)


class CustomerScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Title Card using shared ScreenHeader
        header_card = ScreenHeader(
            title="Customers",
            subtitle="Find customers, add new customers, and view outstanding credit."
        )

        self.pill_total_custs = BadgePill("Customers: 0", BadgePill.TYPE_INFO)
        self.pill_total_debt = BadgePill("Credit Due: Rs. 0.00", BadgePill.TYPE_WARNING)

        header_card.add_pill(self.pill_total_custs)
        header_card.add_pill(self.pill_total_debt)

        layout.addWidget(header_card)

        # Main Content Row
        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        # Left Column: Customers Table Card
        left_card = Card()
        left_layout = left_card.layout()
        left_layout.setSpacing(10)

        bar_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by name or CNIC")
        self.txt_search.textChanged.connect(self.on_search)

        self.btn_add_cust = QPushButton("Add Customer")
        self.btn_add_cust.setObjectName("primaryButton")
        self.btn_add_cust.clicked.connect(self.open_add_customer_dialog)

        bar_layout.addWidget(self.txt_search, 1)
        bar_layout.addWidget(self.btn_add_cust)
        left_layout.addLayout(bar_layout)

        self.tbl_customers = QTableWidget(0, 6)
        self.tbl_customers.setHorizontalHeaderLabels(["CNIC", "First Name", "Last Name", "Email", "City", "Amount Due"])
        self.tbl_customers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_customers.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        polish_table(self.tbl_customers)
        self.tbl_customers.verticalHeader().setVisible(False)
        self.tbl_customers.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_customers.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_customers.itemSelectionChanged.connect(self.on_customer_selected)


        left_layout.addWidget(self.tbl_customers, 1)

        # Right Column: Debt Aging & Profile Detail Panel Card
        right_card = Card()
        flexible_side_panel(right_card, minimum=280, maximum=410)
        right_layout = right_card.layout()
        right_layout.setSpacing(14)

        lbl_profile_title = QLabel("Credit Summary")
        lbl_profile_title.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        right_layout.addWidget(lbl_profile_title)


        self.lbl_selected_cust = QLabel("Select a customer to view their unpaid balance.")
        self.lbl_selected_cust.setObjectName("caption")
        self.lbl_selected_cust.setWordWrap(True)
        self.lbl_selected_cust.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        right_layout.addWidget(self.lbl_selected_cust)

        self.lbl_total_cust_debt = QLabel("Total Due: Rs. 0.00")
        self.lbl_total_cust_debt.setStyleSheet(f" font-weight: 800; color: {ThemeTokens.ACCENT};")
        right_layout.addWidget(self.lbl_total_cust_debt)

        right_layout.addSpacing(10)
        lbl_aging_hdr = QLabel("How long the balance has been due:")
        lbl_aging_hdr.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY};")
        right_layout.addWidget(lbl_aging_hdr)

        aging_box = QFrame()
        aging_box.setObjectName("insetPanel")
        aging_lay = QVBoxLayout(aging_box)
        aging_lay.setSpacing(8)

        self.lbl_age_30 = QLabel("0 - 30 Days: Rs. 0.00")
        self.lbl_age_30.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-weight: 600;")
        self.lbl_age_60 = QLabel("31 - 60 Days: Rs. 0.00")
        self.lbl_age_60.setStyleSheet(f"color: {ThemeTokens.WARNING}; font-weight: 600;")
        self.lbl_age_plus = QLabel("61+ Days: Rs. 0.00")
        self.lbl_age_plus.setStyleSheet(f"color: {ThemeTokens.DANGER}; font-weight: 800;")

        aging_lay.addWidget(self.lbl_age_30)
        aging_lay.addWidget(self.lbl_age_60)
        aging_lay.addWidget(self.lbl_age_plus)

        right_layout.addWidget(aging_box)
        right_layout.addStretch()

        main_row.addWidget(left_card, 7)
        main_row.addWidget(right_card, 3)
        main_row.setStretch(0, 7)
        main_row.setStretch(1, 3)

        layout.addLayout(main_row, 1)

        self.refresh_all_data()

    def refresh_all_data(self):
        custs = _CUSTOMER_CONTROLLER.search_with_debt("")
        self.populate_customers_table(custs)

        total_system_debt = _CUSTOMER_CONTROLLER.khatoo_summary()
        self.pill_total_custs.setText(f"Customers: {len(custs)}")
        self.pill_total_debt.setText(f"Credit Due: Rs. {total_system_debt:.2f}")

    def populate_customers_table(self, custs):
        self.tbl_customers.setRowCount(len(custs))
        for row, item in enumerate(custs):
            if len(item) == 6:
                cnic, fname, lname, email, city, debt = item
            else:
                cnic, fname, lname, email, city = item
                debt = _CUSTOMER_CONTROLLER.total_debt(cnic)

            self.tbl_customers.setItem(row, 0, QTableWidgetItem(str(cnic)))
            self.tbl_customers.setItem(row, 1, QTableWidgetItem(str(fname)))
            self.tbl_customers.setItem(row, 2, QTableWidgetItem(str(lname)))
            self.tbl_customers.setItem(row, 3, QTableWidgetItem(str(email)))
            self.tbl_customers.setItem(row, 4, QTableWidgetItem(str(city)))
            self.tbl_customers.setItem(row, 5, QTableWidgetItem(f"Rs. {float(debt):.2f}"))

    def on_search(self, text):
        custs = _CUSTOMER_CONTROLLER.search_with_debt(text.strip())
        self.populate_customers_table(custs)

    def on_customer_selected(self):
        rows = self.tbl_customers.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        cnic = self.tbl_customers.item(r, 0).text()
        fname = self.tbl_customers.item(r, 1).text()
        lname = self.tbl_customers.item(r, 2).text()

        debt = _CUSTOMER_CONTROLLER.total_debt(cnic)
        aging = _CUSTOMER_CONTROLLER.debt_aging(cnic)

        self.lbl_selected_cust.setText(f"{fname} {lname}\nCNIC: {cnic}")
        self.lbl_total_cust_debt.setText(f"Total Due: Rs. {float(debt):.2f}")

        self.lbl_age_30.setText(f"0 - 30 Days: Rs. {aging['0_30']:.2f}")
        self.lbl_age_60.setText(f"31 - 60 Days: Rs. {aging['31_60']:.2f}")
        self.lbl_age_plus.setText(f"61+ Days: Rs. {aging['61_plus']:.2f}")

    def open_add_customer_dialog(self):
        dlg = AddCustomerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def on_screen_show(self):
        """Auto-refreshes customer directory whenever screen is navigated to."""
        self.refresh_all_data()
