"""Stock and product management views for Pharma-Khaato."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTabWidget, QDialog, QFormLayout,
    QCheckBox, QMessageBox
)
from PySide6.QtCore import QDate

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog, flexible_side_panel

from controllers.inventory_controller import InventoryController

_INVENTORY_CONTROLLER = InventoryController()


class AddProductDialog(QDialog):
    """Register a new product without exposing database terminology."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Product")
        configure_dialog(self, 540, 600, minimum_width=420, minimum_height=420)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeTokens.SURFACE_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
            }}
            QLabel {{ font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
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

        title = QLabel("Add Product")
        title.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Paracetamol 500mg")
        self.txt_name.setAccessibleName("Product name")
        form.addRow("Product name *:", self.txt_name)

        self.spn_price = QDoubleSpinBox()
        self.spn_price.setRange(0.01, 100000.0)
        self.spn_price.setValue(50.0)
        self.spn_price.setPrefix("Rs. ")
        self.spn_price.setDecimals(2)
        self.spn_price.setAccessibleName("Selling price")
        form.addRow("Selling price *:", self.spn_price)

        self.spn_min_stock = QSpinBox()
        self.spn_min_stock.setRange(0, 100000)
        self.spn_min_stock.setValue(10)
        self.spn_min_stock.setAccessibleName("Low stock warning level")
        form.addRow("Low-stock warning at:", self.spn_min_stock)

        self.txt_company = QLineEdit()
        self.txt_company.setPlaceholderText("Manufacturer or company")
        form.addRow("Manufacturer:", self.txt_company)

        self.cmb_category = QComboBox()
        self.cmb_category.addItems(
            ["General", "Surgical", "Antibiotic", "Analgesic", "Cardiology", "OTC", "Other"]
        )
        form.addRow("Category:", self.cmb_category)

        self.txt_formula = QLineEdit()
        self.txt_formula.setPlaceholderText("e.g. Acetaminophen")
        form.addRow("Generic / formula:", self.txt_formula)

        self.txt_barcode = QLineEdit()
        self.txt_barcode.setPlaceholderText("Scan barcode or leave blank")
        form.addRow("Barcode:", self.txt_barcode)

        self.chk_prescription = QCheckBox("Prescription only (Rx)")
        form.addRow("", self.chk_prescription)

        layout.addLayout(form)
        layout.addSpacing(10)

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("Save Product")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        layout.addLayout(buttons)

    def on_save(self):
        name = self.txt_name.text().strip()
        if not name:
            show_toast(self, "Enter a product name.", ToastType.WARNING)
            return

        ok, msg = _INVENTORY_CONTROLLER.register_product(
            name=name,
            price=self.spn_price.value(),
            min_stock=self.spn_min_stock.value(),
            company=self.txt_company.text().strip() or "General",
            category=self.cmb_category.currentText(),
            formula=self.txt_formula.text().strip() or "N/A",
            barcode=self.txt_barcode.text().strip() or None,
            requires_prescription=1 if self.chk_prescription.isChecked() else 0,
        )

        if ok:
            target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(target, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Save Product", msg)


class AddSupplierDialog(QDialog):
    """Create a real supplier before stock is received from them."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Supplier")
        configure_dialog(self, 500, 360, minimum_width=390, minimum_height=300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Add Supplier")
        title.setObjectName("h2")
        layout.addWidget(title)

        form = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Supplier name")
        self.txt_company = QLineEdit()
        self.txt_company.setPlaceholderText("Company name (optional)")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("Phone number")

        form.addRow("Supplier name *:", self.txt_name)
        form.addRow("Company:", self.txt_company)
        form.addRow("Phone *:", self.txt_phone)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save Supplier")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.on_save)
        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        layout.addLayout(buttons)

    def on_save(self):
        name = self.txt_name.text().strip()
        phone = self.txt_phone.text().strip()
        if not name:
            show_toast(self, "Enter the supplier name.", ToastType.WARNING)
            return
        if not phone:
            show_toast(self, "Enter a supplier phone number.", ToastType.WARNING)
            return

        ok, msg = _INVENTORY_CONTROLLER.register_supplier(
            name,
            phone,
            self.txt_company.text().strip() or name,
        )
        if ok:
            show_toast(self, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Save Supplier", msg)


class InventoryScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self.all_products_raw = []
        self._low_stock_names = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Stock & Products",
            "Manage products, receive stock, and catch low-stock or expiry problems early."
        )
        self.pill_total_prods = BadgePill("Products: 0", BadgePill.TYPE_INFO)
        self.pill_low_stock = BadgePill("Low Stock: 0", BadgePill.TYPE_WARNING)
        self.pill_near_expiry = BadgePill("Expiring Soon: 0", BadgePill.TYPE_DANGER)
        header_card.add_pill(self.pill_total_prods)
        header_card.add_pill(self.pill_low_stock)
        header_card.add_pill(self.pill_near_expiry)
        layout.addWidget(header_card)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        self.tab_catalog = QWidget()
        self.setup_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "Products")

        self.tab_intake = QWidget()
        self.setup_intake_tab()
        self.tabs.addTab(self.tab_intake, "Add Stock")

        self.tab_alerts = QWidget()
        self.setup_alerts_tab()
        self.tabs.addTab(self.tab_alerts, "Stock Alerts")

        layout.addWidget(self.tabs, 1)
        self.refresh_all_data()

    def on_screen_show(self):
        self.refresh_all_data()

    def setup_catalog_tab(self):
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        self.txt_catalog_search = QLineEdit()
        self.txt_catalog_search.setPlaceholderText("Search by product, formula, or barcode")
        self.txt_catalog_search.setAccessibleName("Search stock and products")
        self.txt_catalog_search.textChanged.connect(self.on_filter_catalog)

        self.btn_add_prod = QPushButton("Add Product")
        self.btn_add_prod.setObjectName("primaryButton")
        self.btn_add_prod.clicked.connect(self.open_add_product_dialog)

        bar.addWidget(self.txt_catalog_search, 1)
        bar.addWidget(self.btn_add_prod)
        layout.addLayout(bar)

        self.tbl_products = QTableWidget(0, 5)
        self.tbl_products.setHorizontalHeaderLabels(
            ["Product", "Price", "In Stock", "Status", "Action"]
        )
        self.tbl_products.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_products.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        polish_table(self.tbl_products, min_row_height=40)
        self.tbl_products.verticalHeader().setVisible(False)
        self.tbl_products.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_products.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tbl_products, 1)

    def setup_intake_tab(self):
        layout = QHBoxLayout(self.tab_intake)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        form_card = Card()
        flexible_side_panel(form_card, minimum=310, maximum=430)
        form_layout = form_card.layout()

        title = QLabel("Add Stock")
        title.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.ACCENT};")
        form_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.cmb_intake_prod = QComboBox()
        form.addRow("Product *:", self.cmb_intake_prod)

        self.cmb_intake_supp = QComboBox()
        form.addRow("Supplier *:", self.cmb_intake_supp)

        self.btn_add_supplier = QPushButton("Add Supplier")
        self.btn_add_supplier.clicked.connect(self.open_add_supplier_dialog)
        form.addRow("", self.btn_add_supplier)

        self.spn_intake_qty = QSpinBox()
        self.spn_intake_qty.setRange(1, 100000)
        self.spn_intake_qty.setValue(100)
        form.addRow("Quantity *:", self.spn_intake_qty)

        self.dt_expiry = QDateEdit()
        self.dt_expiry.setCalendarPopup(True)
        self.dt_expiry.setDate(QDate.currentDate().addYears(1))
        form.addRow("Expiry date *:", self.dt_expiry)

        self.dt_mfg = QDateEdit()
        self.dt_mfg.setCalendarPopup(True)
        self.dt_mfg.setDate(QDate.currentDate())
        form.addRow("Manufacture date:", self.dt_mfg)

        form_layout.addLayout(form)
        form_layout.addSpacing(14)

        self.btn_submit_intake = QPushButton("Add Stock")
        self.btn_submit_intake.setObjectName("primaryButton")
        self.btn_submit_intake.setMinimumHeight(44)
        self.btn_submit_intake.clicked.connect(self.on_submit_intake)
        form_layout.addWidget(self.btn_submit_intake)
        form_layout.addStretch()

        list_card = Card()
        list_layout = list_card.layout()
        list_title = QLabel("Current Stock by Expiry")
        list_title.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        list_layout.addWidget(list_title)

        self.tbl_batches = QTableWidget(0, 4)
        self.tbl_batches.setHorizontalHeaderLabels(["Product", "Supplier", "Qty", "Expiry"])
        self.tbl_batches.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_batches)
        self.tbl_batches.verticalHeader().setVisible(False)
        self.tbl_batches.setEditTriggers(QTableWidget.NoEditTriggers)
        list_layout.addWidget(self.tbl_batches, 1)

        layout.addWidget(form_card, 3)
        layout.addWidget(list_card, 7)
        layout.setStretch(0, 3)
        layout.setStretch(1, 7)

    def setup_alerts_tab(self):
        layout = QVBoxLayout(self.tab_alerts)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        near_label = QLabel("Expiring in the next 30 days")
        near_label.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.WARNING};")
        layout.addWidget(near_label)

        self.tbl_near_expiry = QTableWidget(0, 4)
        self.tbl_near_expiry.setHorizontalHeaderLabels(["Product", "Supplier", "Qty", "Expiry"])
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_near_expiry)
        self.tbl_near_expiry.verticalHeader().setVisible(False)
        self.tbl_near_expiry.setMinimumHeight(130)
        self.tbl_near_expiry.setMaximumHeight(230)
        layout.addWidget(self.tbl_near_expiry)

        low_label = QLabel("Low stock — reorder soon")
        low_label.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.DANGER};")
        layout.addWidget(low_label)

        self.tbl_low_stock = QTableWidget(0, 3)
        self.tbl_low_stock.setHorizontalHeaderLabels(["Product", "In Stock", "Alert Level"])
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        polish_table(self.tbl_low_stock)
        self.tbl_low_stock.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_low_stock, 1)

    def refresh_all_data(self):
        products = _INVENTORY_CONTROLLER.products()
        low_stock = _INVENTORY_CONTROLLER.low_stock()
        near_expiry = _INVENTORY_CONTROLLER.near_expiry(30)

        self.all_products_raw = list(products)
        self._low_stock_names = {str(item[0]) for item in low_stock}
        self.populate_catalog_table(self.all_products_raw)

        self.pill_total_prods.setText(f"Products: {len(products)}")
        self.pill_low_stock.setText(f"Low Stock: {len(low_stock)}")
        self.pill_near_expiry.setText(f"Expiring Soon: {len(near_expiry)}")

        self.cmb_intake_prod.clear()
        for product_id, product_name, _price, _stock in products:
            self.cmb_intake_prod.addItem(str(product_name), product_id)

        suppliers = _INVENTORY_CONTROLLER.suppliers()
        self.cmb_intake_supp.clear()
        if suppliers:
            for supplier_id, supplier_name, company_name in suppliers:
                label = str(supplier_name)
                if company_name and str(company_name) != str(supplier_name):
                    label = f"{supplier_name} — {company_name}"
                self.cmb_intake_supp.addItem(label, supplier_id)
            self.cmb_intake_supp.setEnabled(True)
            self.btn_submit_intake.setEnabled(bool(products))
        else:
            self.cmb_intake_supp.addItem("Add a supplier first", None)
            self.cmb_intake_supp.setEnabled(False)
            self.btn_submit_intake.setEnabled(False)

        self.populate_batches_table(_INVENTORY_CONTROLLER.active_batches())
        self.populate_alerts_tables(near_expiry, low_stock)

    def populate_catalog_table(self, products):
        self.tbl_products.setRowCount(len(products))
        for row, item in enumerate(products):
            product_id, product_name, price, stock = item
            product_name = str(product_name)
            stock = int(stock or 0)

            self.tbl_products.setItem(row, 0, QTableWidgetItem(product_name))
            self.tbl_products.setItem(row, 1, QTableWidgetItem(f"Rs. {float(price):.2f}"))
            self.tbl_products.setItem(row, 2, QTableWidgetItem(str(stock)))

            if stock <= 0:
                status = "Out of Stock"
            elif product_name in self._low_stock_names:
                status = "Low Stock"
            else:
                status = "In Stock"
            self.tbl_products.setItem(row, 3, QTableWidgetItem(status))

            button = QPushButton("Add Stock")
            button.setProperty("compact", True)
            button.setMinimumWidth(88)
            button.setMaximumWidth(104)
            button.setAccessibleName(f"Add stock for {product_name}")
            button.clicked.connect(
                lambda checked=False, pid=product_id: self.quick_intake_for_product(pid)
            )
            self.tbl_products.setCellWidget(row, 4, button)

    def populate_batches_table(self, batches):
        self.tbl_batches.setRowCount(len(batches))
        for row, item in enumerate(batches):
            _batch_id, product_name, supplier_name, quantity, expiry = item
            self.tbl_batches.setItem(row, 0, QTableWidgetItem(str(product_name)))
            self.tbl_batches.setItem(row, 1, QTableWidgetItem(str(supplier_name)))
            self.tbl_batches.setItem(row, 2, QTableWidgetItem(str(quantity)))
            self.tbl_batches.setItem(row, 3, QTableWidgetItem(str(expiry)))

    def populate_alerts_tables(self, near_expiry, low_stock):
        self.tbl_near_expiry.setRowCount(len(near_expiry))
        for row, item in enumerate(near_expiry):
            _batch_id, product_name, supplier_name, quantity, expiry = item
            self.tbl_near_expiry.setItem(row, 0, QTableWidgetItem(str(product_name)))
            self.tbl_near_expiry.setItem(row, 1, QTableWidgetItem(str(supplier_name)))
            self.tbl_near_expiry.setItem(row, 2, QTableWidgetItem(str(quantity)))
            self.tbl_near_expiry.setItem(row, 3, QTableWidgetItem(str(expiry)))

        self.tbl_low_stock.setRowCount(len(low_stock))
        for row, item in enumerate(low_stock):
            product_name, quantity, alert_level = item
            self.tbl_low_stock.setItem(row, 0, QTableWidgetItem(str(product_name)))
            self.tbl_low_stock.setItem(row, 1, QTableWidgetItem(str(quantity)))
            self.tbl_low_stock.setItem(row, 2, QTableWidgetItem(str(alert_level)))

    def on_filter_catalog(self, text):
        term = text.strip()
        if not term:
            self.populate_catalog_table(self.all_products_raw)
            return

        lowered = term.casefold()
        matching_ids = {
            product_id
            for product_id, product_name, _price, _stock in self.all_products_raw
            if lowered in str(product_name).casefold()
        }

        # Backend search adds formula/barcode matching. Use only its product IDs,
        # then display the canonical product total from all_products_raw rather
        # than a single batch quantity returned by the search query.
        for result in _INVENTORY_CONTROLLER.search_products(term):
            matching_ids.add(result[0])

        filtered = [item for item in self.all_products_raw if item[0] in matching_ids]
        self.populate_catalog_table(filtered)

    def open_add_product_dialog(self):
        dialog = AddProductDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def open_add_supplier_dialog(self):
        dialog = AddSupplierDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def quick_intake_for_product(self, product_id):
        self.tabs.setCurrentIndex(1)
        index = self.cmb_intake_prod.findData(product_id)
        if index >= 0:
            self.cmb_intake_prod.setCurrentIndex(index)

    def on_submit_intake(self):
        product_id = self.cmb_intake_prod.currentData()
        supplier_id = self.cmb_intake_supp.currentData()
        if not product_id:
            show_toast(self, "Choose a product before adding stock.", ToastType.WARNING)
            return
        if not supplier_id:
            show_toast(self, "Add or choose a supplier before adding stock.", ToastType.WARNING)
            return

        manufacture_date = self.dt_mfg.date()
        expiry_date = self.dt_expiry.date()
        today = QDate.currentDate()

        if manufacture_date > today:
            show_toast(self, "Manufacture date cannot be in the future.", ToastType.WARNING)
            return
        if expiry_date <= today:
            show_toast(self, "Expiry date must be in the future.", ToastType.WARNING)
            return
        if manufacture_date >= expiry_date:
            show_toast(self, "Manufacture date must be before the expiry date.", ToastType.WARNING)
            return

        ok, msg = _INVENTORY_CONTROLLER.add_batch(
            product_id,
            supplier_id,
            self.spn_intake_qty.value(),
            expiry_date.toString("yyyy-MM-dd"),
            manufacture_date.toString("yyyy-MM-dd"),
        )
        if ok:
            show_toast(self, msg, ToastType.SUCCESS)
            self.refresh_all_data()
        else:
            QMessageBox.critical(self, "Could Not Add Stock", msg)
