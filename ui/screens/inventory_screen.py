"""
Pharma-Khaato Native PySide6 Stock & Products Screen
Features Master Product Catalog, Add Product Dialog, Batch Shipment Intake, FEFO Expiry Badges, and Low Stock Alerts.
"""

from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTabWidget, QDialog, QFormLayout, QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QDate

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import Toast, ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog, flexible_side_panel

from controllers.inventory_controller import InventoryController

_INVENTORY_CONTROLLER = InventoryController()

class AddProductDialog(QDialog):
    """Modal dialog for registering a new master product."""
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
        title.setStyleSheet(f" font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Paracetamol 500mg")
        form.addRow("Product Name *:", self.txt_name)

        self.spn_price = QDoubleSpinBox()
        self.spn_price.setRange(0.01, 100000.0)
        self.spn_price.setValue(50.0)
        form.addRow("Selling Price *:", self.spn_price)

        self.spn_min_stock = QSpinBox()
        self.spn_min_stock.setRange(1, 1000)
        self.spn_min_stock.setValue(10)
        form.addRow("Low-stock alert at:", self.spn_min_stock)

        self.txt_company = QLineEdit()
        self.txt_company.setText("General")
        form.addRow("Manufacturer:", self.txt_company)

        self.cmb_category = QComboBox()
        self.cmb_category.addItems(["General", "Surgical", "Antibiotic", "Analgesic", "Cardiology", "OTC", "Other"])
        form.addRow("Category:", self.cmb_category)

        self.txt_formula = QLineEdit()
        self.txt_formula.setPlaceholderText("e.g. Acetaminophen")
        form.addRow("Generic / Formula:", self.txt_formula)

        self.txt_barcode = QLineEdit()
        self.txt_barcode.setPlaceholderText("Scan barcode or leave blank")
        form.addRow("Barcode:", self.txt_barcode)

        self.chk_prescription = QCheckBox("Prescription only (Rx)")
        form.addRow("", self.chk_prescription)

        layout.addLayout(form)
        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Save Product")
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
        name = self.txt_name.text().strip()
        if not name:
            show_toast(self, "Enter a product name.", ToastType.WARNING)
            return

        price = self.spn_price.value()
        min_stock = self.spn_min_stock.value()
        company = self.txt_company.text().strip() or "General"
        category = self.cmb_category.currentText()
        formula = self.txt_formula.text().strip() or "N/A"
        barcode = self.txt_barcode.text().strip() or None
        is_rx = 1 if self.chk_prescription.isChecked() else 0

        ok, msg = _INVENTORY_CONTROLLER.register_product(
            name=name, price=price, min_stock=min_stock, company=company,
            category=category, formula=formula, barcode=barcode, requires_prescription=is_rx
        )

        if ok:
            target = self.parent() if hasattr(self.parent(), "show_message_box") else self
            show_toast(target, msg, ToastType.SUCCESS)
            self.accept()
        else:
            QMessageBox.critical(self, "Could Not Save Product", msg)


class InventoryScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Stock & Products",
            "Manage products, add stock batches, and catch low-stock or expiry problems early."
        )
        self.pill_total_prods = BadgePill("Products: 0", BadgePill.TYPE_INFO)
        self.pill_low_stock = BadgePill("Low Stock: 0", BadgePill.TYPE_WARNING)
        self.pill_near_expiry = BadgePill("Near Expiry: 0", BadgePill.TYPE_DANGER)
        header_card.add_pill(self.pill_total_prods)
        header_card.add_pill(self.pill_low_stock)
        header_card.add_pill(self.pill_near_expiry)
        layout.addWidget(header_card)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        # Tab 1: Products
        self.tab_catalog = QWidget()
        self.setup_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "Products")

        # Tab 2: Add Stock
        self.tab_intake = QWidget()
        self.setup_intake_tab()
        self.tabs.addTab(self.tab_intake, "Add Stock")

        # Tab 3: Stock Alerts
        self.tab_alerts = QWidget()
        self.setup_alerts_tab()
        self.tabs.addTab(self.tab_alerts, "Stock Alerts")

        layout.addWidget(self.tabs, 1)

        # Load Data
        self.refresh_all_data()

    def on_screen_show(self):
        """Auto-refreshes inventory catalog and batches whenever screen is navigated to."""
        self.refresh_all_data()

    def setup_catalog_tab(self):
        cat_layout = QVBoxLayout(self.tab_catalog)
        cat_layout.setContentsMargins(14, 14, 14, 14)
        cat_layout.setSpacing(12)

        # Search Bar & Add Button Row
        bar_layout = QHBoxLayout()
        self.txt_catalog_search = QLineEdit()
        self.txt_catalog_search.setPlaceholderText("Search by product, formula, or barcode")
        self.txt_catalog_search.textChanged.connect(self.on_filter_catalog)

        self.btn_add_prod = QPushButton("Add Product")
        self.btn_add_prod.setObjectName("primaryButton")
        self.btn_add_prod.clicked.connect(self.open_add_product_dialog)

        bar_layout.addWidget(self.txt_catalog_search, 1)
        bar_layout.addWidget(self.btn_add_prod)
        cat_layout.addLayout(bar_layout)

        # Products Table
        self.tbl_products = QTableWidget(0, 6)
        self.tbl_products.setHorizontalHeaderLabels(["ID", "Product", "Price", "Stock", "Status", "Action"])
        self.tbl_products.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_products.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        polish_table(self.tbl_products, min_row_height=40)
        self.tbl_products.verticalHeader().setVisible(False)
        self.tbl_products.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_products.setSelectionBehavior(QTableWidget.SelectRows)
        cat_layout.addWidget(self.tbl_products, 1)

    def setup_intake_tab(self):
        intake_layout = QHBoxLayout(self.tab_intake)
        intake_layout.setContentsMargins(14, 14, 14, 14)
        intake_layout.setSpacing(14)

        # Intake Form Card
        form_card = Card()
        flexible_side_panel(form_card, minimum=310, maximum=430)
        f_layout = form_card.layout()

        lbl_f_title = QLabel("Add Stock Batch")
        lbl_f_title.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.ACCENT};")
        f_layout.addWidget(lbl_f_title)

        form = QFormLayout()
        form.setSpacing(12)

        self.cmb_intake_prod = QComboBox()
        form.addRow("Product *:", self.cmb_intake_prod)

        self.cmb_intake_supp = QComboBox()
        form.addRow("Supplier *:", self.cmb_intake_supp)

        self.spn_intake_qty = QSpinBox()
        self.spn_intake_qty.setRange(1, 100000)
        self.spn_intake_qty.setValue(100)
        form.addRow("Quantity *:", self.spn_intake_qty)

        self.dt_expiry = QDateEdit()
        self.dt_expiry.setCalendarPopup(True)
        self.dt_expiry.setDate(QDate.currentDate().addYears(1))
        form.addRow("Expiry Date *:", self.dt_expiry)

        self.dt_mfg = QDateEdit()
        self.dt_mfg.setCalendarPopup(True)
        self.dt_mfg.setDate(QDate.currentDate())
        form.addRow("Manufacture Date:", self.dt_mfg)

        f_layout.addLayout(form)
        f_layout.addSpacing(14)

        self.btn_submit_intake = QPushButton("Add Stock")
        self.btn_submit_intake.setObjectName("primaryButton")
        self.btn_submit_intake.setMinimumHeight(44)
        self.btn_submit_intake.clicked.connect(self.on_submit_intake)
        f_layout.addWidget(self.btn_submit_intake)
        f_layout.addStretch()

        # Batch Stock List View Card
        list_card = Card()
        l_layout = list_card.layout()

        lbl_l_title = QLabel("Available Batches — earliest expiry first")
        lbl_l_title.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        l_layout.addWidget(lbl_l_title)

        self.tbl_batches = QTableWidget(0, 5)
        self.tbl_batches.setHorizontalHeaderLabels(["Batch", "Product", "Supplier", "Qty", "Expiry"])
        self.tbl_batches.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_batches.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        polish_table(self.tbl_batches)
        self.tbl_batches.verticalHeader().setVisible(False)
        self.tbl_batches.setEditTriggers(QTableWidget.NoEditTriggers)
        l_layout.addWidget(self.tbl_batches, 1)

        intake_layout.addWidget(form_card, 3)
        intake_layout.addWidget(list_card, 7)
        intake_layout.setStretch(0, 3)
        intake_layout.setStretch(1, 7)

    def setup_alerts_tab(self):
        alerts_layout = QVBoxLayout(self.tab_alerts)
        alerts_layout.setContentsMargins(14, 14, 14, 14)
        alerts_layout.setSpacing(14)

        # Near Expiry Section
        lbl_near = QLabel("Expiring in the next 30 days")
        lbl_near.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.WARNING};")
        alerts_layout.addWidget(lbl_near)

        self.tbl_near_expiry = QTableWidget(0, 5)
        self.tbl_near_expiry.setHorizontalHeaderLabels(["Batch", "Product", "Supplier", "Qty", "Expiry"])
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_near_expiry.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        polish_table(self.tbl_near_expiry)
        self.tbl_near_expiry.verticalHeader().setVisible(False)
        self.tbl_near_expiry.setMinimumHeight(130)
        self.tbl_near_expiry.setMaximumHeight(230)
        alerts_layout.addWidget(self.tbl_near_expiry)

        # Low Stock Section
        lbl_low = QLabel("Low stock — reorder soon")
        lbl_low.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.DANGER};")
        alerts_layout.addWidget(lbl_low)

        self.tbl_low_stock = QTableWidget(0, 3)
        self.tbl_low_stock.setHorizontalHeaderLabels(["Product", "In Stock", "Alert Level"])
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        polish_table(self.tbl_low_stock)
        self.tbl_low_stock.verticalHeader().setVisible(False)
        alerts_layout.addWidget(self.tbl_low_stock, 1)


    def refresh_all_data(self):
        # 1. Refresh Catalog
        prods = _INVENTORY_CONTROLLER.products()
        self.all_products_raw = prods
        self.populate_catalog_table(prods)

        # Update header summary
        low_stock_list = _INVENTORY_CONTROLLER.low_stock()
        near_expiry_list = _INVENTORY_CONTROLLER.near_expiry(30)

        self.pill_total_prods.setText(f"Products: {len(prods)}")
        self.pill_low_stock.setText(f"Low Stock: {len(low_stock_list)}")
        self.pill_near_expiry.setText(f"Near Expiry: {len(near_expiry_list)}")

        # 2. Populate Intake Product ComboBox
        self.cmb_intake_prod.clear()
        self.prod_id_map = {}
        for p in prods:
            p_id, p_name, p_price, p_stock = p
            display_str = f"{p_name} (ID: {p_id})"
            self.cmb_intake_prod.addItem(display_str, p_id)
            self.prod_id_map[display_str] = p_id

        # Populate Suppliers
        supps = _INVENTORY_CONTROLLER.suppliers()
        self.cmb_intake_supp.clear()
        self.supp_id_map = {}
        if not supps:
            # Ensure at least default supplier
            _INVENTORY_CONTROLLER.register_supplier("Default Supplier", "03000000000", "Pharma Supplier Co")
            supps = _INVENTORY_CONTROLLER.suppliers()

        for s in supps:
            s_id, s_name, s_comp = s
            d_str = f"{s_name} - {s_comp}"
            self.cmb_intake_supp.addItem(d_str, s_id)
            self.supp_id_map[d_str] = s_id

        # Populate Batches List
        all_active_batches = _INVENTORY_CONTROLLER.active_batches()
        self.populate_batches_table(all_active_batches)

        # 3. Populate Alerts Tab
        self.populate_alerts_tables(near_expiry_list, low_stock_list)

    def populate_catalog_table(self, prods):
        self.tbl_products.setRowCount(len(prods))
        for row, item in enumerate(prods):
            p_id, p_name, p_price, p_stock = item
            self.tbl_products.setItem(row, 0, QTableWidgetItem(str(p_id)))
            self.tbl_products.setItem(row, 1, QTableWidgetItem(str(p_name)))
            self.tbl_products.setItem(row, 2, QTableWidgetItem(f"{p_price:.2f}"))
            self.tbl_products.setItem(row, 3, QTableWidgetItem(str(p_stock)))

            status_str = "In Stock" if p_stock > 10 else ("Low Stock" if p_stock > 0 else "Out of Stock")
            self.tbl_products.setItem(row, 4, QTableWidgetItem(status_str))

            btn_add_stock = QPushButton("Add Stock")
            btn_add_stock.setProperty("compact", True)
            btn_add_stock.setMinimumWidth(88)
            btn_add_stock.clicked.connect(lambda checked=False, pid=p_id: self.quick_intake_for_product(pid))
            self.tbl_products.setCellWidget(row, 5, btn_add_stock)


    def populate_batches_table(self, batches):
        self.tbl_batches.setRowCount(len(batches))
        for row, item in enumerate(batches):
            b_id, p_name, s_name, b_qty, b_exp = item
            self.tbl_batches.setItem(row, 0, QTableWidgetItem(f"Batch #{b_id}"))
            self.tbl_batches.setItem(row, 1, QTableWidgetItem(str(p_name)))
            self.tbl_batches.setItem(row, 2, QTableWidgetItem(str(s_name)))
            self.tbl_batches.setItem(row, 3, QTableWidgetItem(str(b_qty)))
            self.tbl_batches.setItem(row, 4, QTableWidgetItem(str(b_exp)))

    def populate_alerts_tables(self, near_expiry, low_stock):
        self.tbl_near_expiry.setRowCount(len(near_expiry))
        for row, item in enumerate(near_expiry):
            b_id, p_name, s_name, b_qty, b_exp = item
            self.tbl_near_expiry.setItem(row, 0, QTableWidgetItem(f"Batch #{b_id}"))
            self.tbl_near_expiry.setItem(row, 1, QTableWidgetItem(str(p_name)))
            self.tbl_near_expiry.setItem(row, 2, QTableWidgetItem(str(s_name)))
            self.tbl_near_expiry.setItem(row, 3, QTableWidgetItem(str(b_qty)))
            self.tbl_near_expiry.setItem(row, 4, QTableWidgetItem(str(b_exp)))

        self.tbl_low_stock.setRowCount(len(low_stock))
        for row, item in enumerate(low_stock):
            p_name, qty, min_stk = item
            self.tbl_low_stock.setItem(row, 0, QTableWidgetItem(str(p_name)))
            self.tbl_low_stock.setItem(row, 1, QTableWidgetItem(str(qty)))
            self.tbl_low_stock.setItem(row, 2, QTableWidgetItem(str(min_stk)))

    def on_filter_catalog(self, text):
        term = text.strip()
        if not term:
            self.populate_catalog_table(self.all_products_raw)
            return

        filtered = _INVENTORY_CONTROLLER.search_products(term)
        # Adapt format: search_products returns (p_id, p_name, p_price, b_id, b_qty, b_exp)
        # Unique by product ID
        prod_map = {}
        for item in filtered:
            p_id, p_name, p_price, b_id, b_qty, b_exp = item
            if p_id not in prod_map:
                prod_map[p_id] = (p_id, p_name, p_price, b_qty)
        self.populate_catalog_table(list(prod_map.values()))

    def open_add_product_dialog(self):
        dlg = AddProductDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_all_data()

    def quick_intake_for_product(self, prod_id):
        self.tabs.setCurrentIndex(1)
        index = self.cmb_intake_prod.findData(prod_id)
        if index >= 0:
            self.cmb_intake_prod.setCurrentIndex(index)

    def on_submit_intake(self):
        prod_id = self.cmb_intake_prod.currentData()
        supp_id = self.cmb_intake_supp.currentData()
        qty = self.spn_intake_qty.value()
        exp_date = self.dt_expiry.date().toString("yyyy-MM-dd")
        mfg_date = self.dt_mfg.date().toString("yyyy-MM-dd")

        if not prod_id or not supp_id:
            show_toast(self, "Choose a product and supplier before adding stock.", ToastType.WARNING)
            return

        ok, msg = _INVENTORY_CONTROLLER.add_batch(prod_id, supp_id, qty, exp_date, mfg_date)
        if ok:
            show_toast(self, msg, ToastType.SUCCESS)
            self.refresh_all_data()
        else:
            QMessageBox.critical(self, "Could Not Add Stock", msg)
