"""Stock and product management views for Pharma-Khaato."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTabWidget, QDialog, QFormLayout,
    QCheckBox, QMessageBox,
)
from PySide6.QtCore import QDate, QTimer, Qt

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import configure_dialog, flexible_side_panel
from ui.app.async_tasks import AsyncTaskRunner

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
    """Inventory UI optimized for bounded, asynchronous reads."""

    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._tasks = AsyncTaskRunner(self)
        self.all_products_raw = []
        self._product_by_id = {}
        self._visible_products = []
        self._low_stock_names = set()
        self._low_stock_raw = []
        self._near_expiry_raw = []
        self._intake_loaded = False
        self._intake_loading = False
        self._pending_intake_product_id = None
        self._stock_write_in_progress = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Stock & Products",
            "Manage products, receive stock, and catch low-stock or expiry problems early."
        )
        self.pill_total_prods = BadgePill("Products: …", BadgePill.TYPE_INFO)
        self.pill_low_stock = BadgePill("Low Stock: …", BadgePill.TYPE_WARNING)
        self.pill_near_expiry = BadgePill("Expiring Soon: …", BadgePill.TYPE_DANGER)
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

        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)
        self.refresh_catalog_data()

    def on_screen_show(self):
        self.refresh_catalog_data()
        self._refresh_visible_tab()

    def setup_catalog_tab(self):
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        self.txt_catalog_search = QLineEdit()
        self.txt_catalog_search.setPlaceholderText("Search by product, formula, or barcode")
        self.txt_catalog_search.setAccessibleName("Search stock and products")

        self.catalog_search_timer = QTimer(self)
        self.catalog_search_timer.setSingleShot(True)
        self.catalog_search_timer.setInterval(160)
        self.catalog_search_timer.timeout.connect(self._run_catalog_filter)
        self.txt_catalog_search.textChanged.connect(self._queue_catalog_filter)

        self.btn_selected_stock = QPushButton("Add Stock")
        self.btn_selected_stock.setEnabled(False)
        self.btn_selected_stock.setToolTip("Select a product first")
        self.btn_selected_stock.clicked.connect(self.quick_intake_selected)

        self.btn_add_prod = QPushButton("Add Product")
        self.btn_add_prod.setObjectName("primaryButton")
        self.btn_add_prod.clicked.connect(self.open_add_product_dialog)

        bar.addWidget(self.txt_catalog_search, 1)
        bar.addWidget(self.btn_selected_stock)
        bar.addWidget(self.btn_add_prod)
        layout.addLayout(bar)

        self.lbl_catalog_status = QLabel("Loading products…")
        self.lbl_catalog_status.setObjectName("caption")
        layout.addWidget(self.lbl_catalog_status)

        self.tbl_products = QTableWidget(0, 4)
        self.tbl_products.setHorizontalHeaderLabels(
            ["Product", "Price", "In Stock", "Status"]
        )
        self.tbl_products.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_products.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_products.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_products, min_row_height=38)
        self.tbl_products.verticalHeader().setVisible(False)
        self.tbl_products.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_products.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_products.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_products.itemSelectionChanged.connect(self._update_catalog_actions)
        self.tbl_products.doubleClicked.connect(lambda *_: self.quick_intake_selected())
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

        self.lbl_intake_status = QLabel("Stock details load when this tab is opened.")
        self.lbl_intake_status.setWordWrap(True)
        self.lbl_intake_status.setObjectName("caption")
        form_layout.addWidget(self.lbl_intake_status)

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
        self.btn_submit_intake.setEnabled(False)
        form_layout.addWidget(self.btn_submit_intake)
        form_layout.addStretch()

        list_card = Card()
        list_layout = list_card.layout()
        list_title = QLabel("Current Stock by Expiry (nearest 300 batches)")
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

    def _on_tab_changed(self, _index):
        self._refresh_visible_tab()

    def _refresh_visible_tab(self):
        index = self.tabs.currentIndex()
        if index == 1 and not self._intake_loaded:
            self._load_intake_data()
        elif index == 2:
            self.populate_alerts_tables(self._near_expiry_raw, self._low_stock_raw)

    def refresh_catalog_data(self):
        self.pill_total_prods.setText("Products: …")
        self.pill_low_stock.setText("Low Stock: …")
        self.pill_near_expiry.setText("Expiring Soon: …")
        if not self.all_products_raw:
            self.lbl_catalog_status.setText("Loading products…")

        self._tasks.run_latest(
            "inventory-catalog",
            lambda: _INVENTORY_CONTROLLER.catalog_snapshot(400, 100),
            self._apply_catalog_snapshot,
            lambda _details: self._catalog_load_failed(),
        )

    def _apply_catalog_snapshot(self, snapshot):
        products = list(snapshot.get("products") or [])
        low_stock = list(snapshot.get("low_stock") or [])
        near_expiry = list(snapshot.get("near_expiry") or [])

        self.all_products_raw = products
        self._product_by_id.update({item[0]: item for item in products})
        self._low_stock_raw = low_stock
        self._near_expiry_raw = near_expiry
        self._low_stock_names = {str(item[0]) for item in low_stock}

        total = int(snapshot.get("total_products", len(products)) or 0)
        low_count = int(snapshot.get("low_stock_count", len(low_stock)) or 0)
        near_count = int(snapshot.get("near_expiry_count", len(near_expiry)) or 0)
        self.pill_total_prods.setText(f"Products: {total}")
        self.pill_low_stock.setText(f"Low Stock: {low_count}")
        self.pill_near_expiry.setText(f"Expiring Soon: {near_count}")

        term = self.txt_catalog_search.text().strip()
        if term:
            self._run_catalog_filter()
        else:
            self.populate_catalog_table(products)
            if total > len(products):
                self.lbl_catalog_status.setText(
                    f"Showing first {len(products)} of {total} products. Search finds the full catalog."
                )
            else:
                self.lbl_catalog_status.setText(f"Showing {len(products)} products.")

        self._intake_loaded = False
        if self.tabs.currentIndex() == 1:
            self._load_intake_data()
        elif self.tabs.currentIndex() == 2:
            self.populate_alerts_tables(near_expiry, low_stock)

    def _catalog_load_failed(self):
        self.pill_total_prods.setText("Products: unavailable")
        self.pill_low_stock.setText("Low Stock: unavailable")
        self.pill_near_expiry.setText("Expiring: unavailable")
        self.lbl_catalog_status.setText("Could not load inventory. Try opening the screen again.")
        if self.show_message_box:
            show_toast(self, "Could not load inventory data.", ToastType.WARNING)

    def refresh_all_data(self):
        self.refresh_catalog_data()
        self._refresh_visible_tab()

    def _sync_product_combo(self):
        selected_id = self._pending_intake_product_id or self.cmb_intake_prod.currentData()
        rows = list(self.all_products_raw)
        if selected_id is not None and selected_id not in {item[0] for item in rows}:
            extra = self._product_by_id.get(selected_id)
            if extra:
                rows.append(extra)

        self.cmb_intake_prod.blockSignals(True)
        self.cmb_intake_prod.clear()
        for item in rows:
            product_id, product_name = item[0], item[1]
            self.cmb_intake_prod.addItem(str(product_name), product_id)
        if selected_id is not None:
            index = self.cmb_intake_prod.findData(selected_id)
            if index >= 0:
                self.cmb_intake_prod.setCurrentIndex(index)
        self.cmb_intake_prod.blockSignals(False)
        self._pending_intake_product_id = None

    def _load_intake_data(self):
        if self._intake_loading:
            return
        self._intake_loading = True
        self._intake_loaded = False
        self.lbl_intake_status.setText("Loading suppliers and current batches…")
        self.btn_submit_intake.setEnabled(False)
        self._sync_product_combo()

        def load():
            return _INVENTORY_CONTROLLER.suppliers(), _INVENTORY_CONTROLLER.active_batches(300)

        self._tasks.run_latest(
            "inventory-intake",
            load,
            self._apply_intake_data,
            lambda _details: self._intake_load_failed(),
        )

    def _apply_intake_data(self, payload):
        suppliers, batches = payload
        self._intake_loading = False
        self._sync_product_combo()

        selected_supplier = self.cmb_intake_supp.currentData()
        self.cmb_intake_supp.blockSignals(True)
        self.cmb_intake_supp.clear()
        if suppliers:
            for supplier_id, supplier_name, company_name in suppliers:
                label = str(supplier_name)
                if company_name and str(company_name) != str(supplier_name):
                    label = f"{supplier_name} — {company_name}"
                self.cmb_intake_supp.addItem(label, supplier_id)
            if selected_supplier is not None:
                index = self.cmb_intake_supp.findData(selected_supplier)
                if index >= 0:
                    self.cmb_intake_supp.setCurrentIndex(index)
            self.cmb_intake_supp.setEnabled(True)
            self.btn_submit_intake.setEnabled(bool(self.cmb_intake_prod.count()))
            self.lbl_intake_status.setText("Ready to receive stock.")
        else:
            self.cmb_intake_supp.addItem("Add a supplier first", None)
            self.cmb_intake_supp.setEnabled(False)
            self.btn_submit_intake.setEnabled(False)
            self.lbl_intake_status.setText("Add a supplier before receiving stock.")
        self.cmb_intake_supp.blockSignals(False)

        self.populate_batches_table(batches or [])
        self._intake_loaded = True

    def _intake_load_failed(self):
        self._intake_loading = False
        self._intake_loaded = False
        self.btn_submit_intake.setEnabled(False)
        self.lbl_intake_status.setText("Could not load suppliers or batches. Switch tabs and try again.")

    def populate_catalog_table(self, products):
        products = list(products or [])
        self._visible_products = products
        self._product_by_id.update({item[0]: item for item in products})
        self.tbl_products.blockSignals(True)
        self.tbl_products.setUpdatesEnabled(False)
        try:
            self.tbl_products.clearContents()
            self.tbl_products.setRowCount(len(products))
            for row, item in enumerate(products):
                product_id, product_name, price, stock = item[:4]
                reorder_level = int(item[4] or 0) if len(item) > 4 else None
                product_name = str(product_name)
                stock = int(stock or 0)

                product_item = QTableWidgetItem(product_name)
                product_item.setData(Qt.ItemDataRole.UserRole, product_id)
                self.tbl_products.setItem(row, 0, product_item)
                self.tbl_products.setItem(row, 1, QTableWidgetItem(f"Rs. {float(price):.2f}"))
                self.tbl_products.setItem(row, 2, QTableWidgetItem(str(stock)))

                if stock <= 0:
                    status = "Out of Stock"
                elif reorder_level is not None and stock <= reorder_level:
                    status = "Low Stock"
                elif product_name in self._low_stock_names:
                    status = "Low Stock"
                else:
                    status = "In Stock"
                self.tbl_products.setItem(row, 3, QTableWidgetItem(status))
        finally:
            self.tbl_products.setUpdatesEnabled(True)
            self.tbl_products.blockSignals(False)
        self._update_catalog_actions()

    def populate_batches_table(self, batches):
        self.tbl_batches.setUpdatesEnabled(False)
        try:
            self.tbl_batches.setRowCount(len(batches))
            for row, item in enumerate(batches):
                _batch_id, product_name, supplier_name, quantity, expiry = item
                self.tbl_batches.setItem(row, 0, QTableWidgetItem(str(product_name)))
                self.tbl_batches.setItem(row, 1, QTableWidgetItem(str(supplier_name)))
                self.tbl_batches.setItem(row, 2, QTableWidgetItem(str(quantity)))
                self.tbl_batches.setItem(row, 3, QTableWidgetItem(str(expiry)))
        finally:
            self.tbl_batches.setUpdatesEnabled(True)

    def populate_alerts_tables(self, near_expiry, low_stock):
        self.tbl_near_expiry.setUpdatesEnabled(False)
        self.tbl_low_stock.setUpdatesEnabled(False)
        try:
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
        finally:
            self.tbl_near_expiry.setUpdatesEnabled(True)
            self.tbl_low_stock.setUpdatesEnabled(True)

    def _queue_catalog_filter(self, *_):
        self.catalog_search_timer.start()

    def _run_catalog_filter(self):
        term = self.txt_catalog_search.text().strip()
        if not term:
            self._tasks.invalidate("inventory-search")
            self.populate_catalog_table(self.all_products_raw)
            self.lbl_catalog_status.setText(f"Showing {len(self.all_products_raw)} loaded products.")
            return

        lowered = term.casefold()
        immediate = [
            item for item in self.all_products_raw
            if lowered in str(item[1]).casefold()
        ]
        if immediate:
            self.populate_catalog_table(immediate)
        self.lbl_catalog_status.setText("Searching full product catalog…")

        def complete(rows):
            if self.txt_catalog_search.text().strip() != term:
                return
            rows = list(rows or [])
            self.populate_catalog_table(rows)
            self.lbl_catalog_status.setText(
                f"{len(rows)} match{'es' if len(rows) != 1 else ''} found."
                if rows else "No matching product found."
            )

        self._tasks.run_latest(
            "inventory-search",
            lambda: _INVENTORY_CONTROLLER.catalog_search(term, 150),
            complete,
            lambda _details: self._catalog_search_failed(term),
        )

    def _catalog_search_failed(self, term):
        if self.txt_catalog_search.text().strip() == term:
            self.lbl_catalog_status.setText("Search could not be completed. Try again.")

    def on_filter_catalog(self, _text):
        self._queue_catalog_filter()

    def _selected_product_id(self):
        selected = self.tbl_products.selectionModel().selectedRows()
        if not selected:
            return None
        item = self.tbl_products.item(selected[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_catalog_actions(self):
        selected = self._selected_product_id() is not None
        self.btn_selected_stock.setEnabled(selected)
        self.btn_selected_stock.setToolTip(
            "Receive stock for the selected product" if selected else "Select a product first"
        )

    def quick_intake_selected(self):
        product_id = self._selected_product_id()
        if product_id is None:
            show_toast(self, "Select a product first.", ToastType.INFO)
            return
        self.quick_intake_for_product(product_id)

    def open_add_product_dialog(self):
        dialog = AddProductDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_catalog_data()

    def open_add_supplier_dialog(self):
        dialog = AddSupplierDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._intake_loaded = False
            self._load_intake_data()

    def quick_intake_for_product(self, product_id):
        self._pending_intake_product_id = product_id
        self.tabs.setCurrentIndex(1)
        if self._intake_loaded:
            self._sync_product_combo()
        else:
            self._load_intake_data()

    def on_submit_intake(self):
        if self._stock_write_in_progress:
            return
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

        args = (
            product_id,
            supplier_id,
            self.spn_intake_qty.value(),
            expiry_date.toString("yyyy-MM-dd"),
            manufacture_date.toString("yyyy-MM-dd"),
        )
        self._stock_write_in_progress = True
        self.btn_submit_intake.setEnabled(False)
        self.btn_submit_intake.setText("Adding Stock…")

        self._tasks.run(
            lambda: _INVENTORY_CONTROLLER.add_batch(*args),
            self._stock_write_complete,
            lambda _details: self._stock_write_failed(),
        )

    def _stock_write_complete(self, result):
        self._stock_write_in_progress = False
        self.btn_submit_intake.setText("Add Stock")
        ok, msg = result
        if ok:
            show_toast(self, msg, ToastType.SUCCESS)
            self._intake_loaded = False
            self.refresh_catalog_data()
            self._load_intake_data()
        else:
            self.btn_submit_intake.setEnabled(True)
            QMessageBox.critical(self, "Could Not Add Stock", msg)

    def _stock_write_failed(self):
        self._stock_write_in_progress = False
        self.btn_submit_intake.setText("Add Stock")
        self.btn_submit_intake.setEnabled(True)
        QMessageBox.critical(
            self,
            "Could Not Add Stock",
            "The stock update could not be completed. Try again.",
        )
