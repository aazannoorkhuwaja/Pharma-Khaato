"""
Pharma-Khaato Native PySide6 POS Billing Screen
Features debounced live search, keyboard-only table navigation, cart row deletion via Delete key, non-blocking toast notifications, and F1-F12 hotkey matrix.
"""

import copy
import json
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QTableView, QHeaderView, QComboBox, QDoubleSpinBox,
    QMessageBox, QFrame, QDialog, QApplication, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QKeySequence, QShortcut

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.hotkey_badge import HotkeyBadge
from ui.widgets.toast import Toast, ToastType
from ui.widgets.pos_models import ProductCatalogModel
from ui.widgets.responsive import flexible_side_panel
from ui.widgets.semantic_style import set_tone
from ui.widgets.pos_widgets import (
    SearchLineEdit, SearchResultsTable, CartTableWidget, RecallSaleDialog,
)
from ui.app.state.session_state import SessionState
from controllers.pos_controller import POSController
from ui.ux_copy import PAYMENT_OPTIONS

_POS_CONTROLLER = POSController()



class POSScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self.session = SessionState.get_instance()
        self.selected_customer_cnic = None
        self.is_customer_verified = False
        self._cart_undo_cache = []
        self.search_results_data = []
        self._checkout_in_progress = False

        self._last_search_key_time = 0.0
        self.search_catalog_model = ProductCatalogModel(self)

        # Debounced Search Timers (150ms)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_live_search)

        self.cust_search_timer = QTimer(self)
        self.cust_search_timer.setSingleShot(True)
        self.cust_search_timer.timeout.connect(self.perform_customer_search)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Search & Cart Table (70% width)
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Header Title & Search Input Card
        search_card = Card()
        search_layout = search_card.layout()

        s_header = QHBoxLayout()
        lbl_title = QLabel("New Sale")
        lbl_title.setObjectName("h1")
        lbl_title.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 800;")
        lbl_title.setWordWrap(True)
        
        hk_layout = QHBoxLayout()
        hk_layout.setSpacing(6)
        self.hotkey_badges = []
        for shortcut, label in [
            ("F1", "Find"), ("F2", "Customer"), ("F3", "Discount"),
            ("F4", "Payment"), ("F5", "Hold"), ("F6", "Resume"),
            ("F12", "Pay"),
        ]:
            badge = HotkeyBadge(shortcut, label)
            self.hotkey_badges.append(badge)
            hk_layout.addWidget(badge)

        s_header.addWidget(lbl_title)
        s_header.addStretch()
        s_header.addLayout(hk_layout)

        search_layout.addLayout(s_header)

        # Barcode & Search Input with Live Debounce & Arrow Navigation
        self.txt_search = SearchLineEdit(
            on_down_callback=self.on_search_input_arrow_down,
            on_escape_callback=self.hide_search_table
        )
        self.txt_search.setPlaceholderText("Scan barcode or search by product name or formula")
        self.txt_search.setAccessibleName("Find product")
        self.txt_search.setAccessibleDescription("Scan a barcode or type a product name or formula.")
        self.txt_search.setObjectName("primarySearch")
        self.txt_search.textChanged.connect(self.on_search_text_changed)
        self.txt_search.returnPressed.connect(self.on_search_submit)
        search_layout.addWidget(self.txt_search)

        left_col.addWidget(search_card)

        # Search Results Quick Picker Table (Keyboard & Double-click navigable)
        self.search_table = SearchResultsTable(
            on_select_callback=self.add_product_from_search_table,
            on_cancel_callback=self.hide_search_table
        )
        self.search_table.setModel(self.search_catalog_model)
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.search_table.verticalHeader().setVisible(False)
        self.search_table.setMinimumHeight(0)
        self.search_table.setMaximumHeight(0)
        self.search_table.hide()
        self.search_table.doubleClicked.connect(self.on_search_table_double_clicked)
        left_col.addWidget(self.search_table)

        # Active Cart Table Card (Delete key row removal supported)
        cart_card = Card()
        cart_layout = cart_card.layout()

        c_header = QLabel("Items in this sale  •  Delete removes item  •  + / − changes quantity")
        c_header.setObjectName("h2")
        cart_layout.addWidget(c_header)

        self.cart_table = CartTableWidget(
            on_delete_callback=self.remove_cart_row,
            on_qty_change_callback=self.on_cart_qty_delta
        )
        self.cart_table.setAccessibleName("Active Cart Items Table")
        self.cart_table.setHorizontalHeaderLabels(["Product", "Batch", "Price", "Qty", "Amount", "In Stock"])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.itemChanged.connect(self.on_cart_cell_changed)

        # Empty-state hint: counter staff must never wonder if a scan registered.
        from ui.widgets.table_polish import polish_table
        polish_table(self.cart_table)
        self.lbl_cart_empty = QLabel("No items yet — scan a barcode or search for a product")
        self.lbl_cart_empty.setAlignment(Qt.AlignCenter)
        self.lbl_cart_empty.setObjectName("emptyState")

        cart_layout.addWidget(self.cart_table)
        cart_layout.addWidget(self.lbl_cart_empty)
        left_col.addWidget(cart_card, 1)


        # Right Column: Summary & Checkout Card (30% width)
        right_card = Card()
        flexible_side_panel(right_card, minimum=292, maximum=420)
        right_layout = right_card.layout()
        right_layout.setSpacing(14)

        # Keep the payment summary usable on short laptop screens without
        # compressing labels/inputs into each other. Primary checkout actions
        # stay pinned below this scrollable summary.
        summary_scroll = QScrollArea()
        summary_scroll.setWidgetResizable(True)
        summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
        summary_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        summary_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        summary_scroll.setObjectName("paymentSummaryScroll")
        summary_body = QWidget()
        summary_body.setObjectName("paymentSummaryBody")
        summary_layout = QVBoxLayout(summary_body)
        summary_layout.setContentsMargins(0, 0, 4, 0)
        summary_layout.setSpacing(12)
        summary_scroll.setWidget(summary_body)

        summary_title = QLabel("Payment")
        summary_title.setObjectName("h2")
        summary_layout.addWidget(summary_title)

        # Customer Selection
        lbl_cust = QLabel("Customer (optional):")
        self.txt_customer = QLineEdit()
        self.txt_customer.setPlaceholderText("Walk-in customer — search by name or CNIC")
        self.txt_customer.setAccessibleName("Find customer")
        self.txt_customer.textChanged.connect(self.on_cust_text_changed)
        self.txt_customer.editingFinished.connect(self.on_customer_lookup)
        summary_layout.addWidget(lbl_cust)
        summary_layout.addWidget(self.txt_customer)

        self.cust_table = QTableWidget(0, 3)
        self.cust_table.setHorizontalHeaderLabels(["Name", "CNIC", "City"])
        self.cust_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cust_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cust_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cust_table.verticalHeader().setVisible(False)
        self.cust_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cust_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cust_table.setMinimumHeight(96)
        self.cust_table.setMaximumHeight(180)
        self.cust_table.hide()
        self.cust_table.doubleClicked.connect(self.on_cust_table_double_clicked)
        summary_layout.addWidget(self.cust_table)

        self.cust_search_data = []

        self.lbl_cust_status = QLabel("Walk-in customer")
        self.lbl_cust_status.setWordWrap(True)
        set_tone(self.lbl_cust_status, "muted")
        summary_layout.addWidget(self.lbl_cust_status)

        summary_layout.addSpacing(6)

        # Payment Method
        lbl_pay = QLabel("Pay with:")
        self.cmb_pay_method = QComboBox()
        for display_label, backend_value in PAYMENT_OPTIONS:
            self.cmb_pay_method.addItem(display_label, backend_value)
        self.cmb_pay_method.setToolTip("Choose how the customer is paying. Customer Credit requires a registered customer.")
        self.cmb_pay_method.currentIndexChanged.connect(self._on_payment_method_changed)
        summary_layout.addWidget(lbl_pay)
        summary_layout.addWidget(self.cmb_pay_method)

        summary_layout.addSpacing(6)

        # Financial Breakdown
        fin_frame = QFrame()
        fin_frame.setObjectName("insetPanel")
        fin_layout = QVBoxLayout(fin_frame)

        self.lbl_subtotal = QLabel("Subtotal: Rs. 0.00")
        set_tone(self.lbl_subtotal, "primary", "bold")

        disc_row = QHBoxLayout()
        disc_row.addWidget(QLabel("Discount:"))
        self.spn_discount = QDoubleSpinBox()
        self.spn_discount.setRange(0.0, 100000.0)
        self.spn_discount.setAccessibleName("Discount amount")
        self.spn_discount.valueChanged.connect(self.refresh_cart_display)
        disc_row.addWidget(self.spn_discount)

        cash_rec_row = QHBoxLayout()
        self.lbl_cash_received = QLabel("Cash received:")
        cash_rec_row.addWidget(self.lbl_cash_received)
        self.spn_cash_received = QDoubleSpinBox()
        self.spn_cash_received.setRange(0.0, 1000000.0)
        self.spn_cash_received.setAccessibleName("Cash received")
        self.spn_cash_received.valueChanged.connect(self.refresh_cart_display)
        cash_rec_row.addWidget(self.spn_cash_received)

        self.lbl_total = QLabel("Total: Rs. 0.00")
        self.lbl_total.setObjectName("posTotal")
        self.lbl_total.setWordWrap(True)

        self.lbl_tax = QLabel("Tax: Rs. 0.00")
        set_tone(self.lbl_tax, "secondary", "bold")

        self.lbl_change = QLabel("Change: Rs. 0.00")
        set_tone(self.lbl_change, "success", "bold")

        fin_layout.addWidget(self.lbl_subtotal)
        fin_layout.addLayout(disc_row)
        fin_layout.addLayout(cash_rec_row)
        fin_layout.addSpacing(8)
        fin_layout.addWidget(self.lbl_tax)
        fin_layout.addWidget(self.lbl_total)
        fin_layout.addWidget(self.lbl_change)

        summary_layout.addWidget(fin_frame)
        summary_layout.addStretch()
        right_layout.addWidget(summary_scroll, 1)

        # Action Buttons
        self.btn_checkout = QPushButton("Complete Sale (F10)")
        self.btn_checkout.setObjectName("primaryButton")
        self.btn_checkout.setAccessibleName("Complete sale")
        self.btn_checkout.setMinimumHeight(44)
        self.btn_checkout.clicked.connect(self.on_checkout)

        btn_hold_row = QHBoxLayout()
        self.btn_hold = QPushButton("Hold Sale (F5)")
        self.btn_hold.clicked.connect(self.on_hold_sale)
        self.btn_recall = QPushButton("Resume Sale (F6)")
        self.btn_recall.clicked.connect(self.on_recall_sale)
        btn_hold_row.addWidget(self.btn_hold)
        btn_hold_row.addWidget(self.btn_recall)

        self.btn_clear = QPushButton("Clear Sale")
        self.btn_clear.clicked.connect(self.on_clear_cart_requested)

        right_layout.addWidget(self.btn_checkout)
        right_layout.addLayout(btn_hold_row)
        right_layout.addWidget(self.btn_clear)
        self._on_payment_method_changed()

        layout.addLayout(left_col, 7)
        layout.addWidget(right_card, 3)
        layout.setStretch(0, 7)
        layout.setStretch(1, 3)

        # Transient Non-blocking Toast Banner
        self.toast = Toast(self)

        # Setup F1-F12 Hotkey Matrix
        self.setup_hotkeys()

    def resizeEvent(self, event):
        compact = event.size().width() < 1000
        for badge in getattr(self, "hotkey_badges", []):
            badge.set_compact(compact)
        super().resizeEvent(event)

    def setup_hotkeys(self):
        self.sc_f1 = QShortcut(QKeySequence("F1"), self, activated=self.txt_search.setFocus)
        self.sc_f2 = QShortcut(QKeySequence("F2"), self, activated=self.txt_customer.setFocus)
        self.sc_f3 = QShortcut(QKeySequence("F3"), self, activated=self.spn_discount.setFocus)
        self.sc_f4 = QShortcut(QKeySequence("F4"), self, activated=self.toggle_pay_method)
        self.sc_f5 = QShortcut(QKeySequence("F5"), self, activated=self.on_hold_sale)
        self.sc_f6 = QShortcut(QKeySequence("F6"), self, activated=self.on_recall_sale)
        self.sc_f10 = QShortcut(QKeySequence("F10"), self, activated=self.on_checkout)
        self.sc_f12 = QShortcut(QKeySequence("F12"), self, activated=self.on_checkout)
        self.sc_esc = QShortcut(QKeySequence("Esc"), self, activated=self._on_escape)
        self.sc_clear = QShortcut(QKeySequence("Ctrl+Delete"), self, activated=self.on_clear_cart_requested)

    def _on_escape(self):
        if self.search_table.isVisible():
            self.search_table.hide()
            self.search_table.setMinimumHeight(0)
            self.search_table.setMaximumHeight(0)
        elif self.txt_search.hasFocus():
            self.txt_search.clear()
            self.txt_search.clearFocus()

    def _on_payment_method_changed(self, *_):
        """Prevent irrelevant cash-entry mistakes for non-cash payments."""
        is_cash = (self.cmb_pay_method.currentData() or self.cmb_pay_method.currentText()) == "Cash"
        self.spn_cash_received.setEnabled(is_cash)
        self.lbl_cash_received.setEnabled(is_cash)
        if not is_cash and self.spn_cash_received.value() != 0.0:
            self.spn_cash_received.setValue(0.0)
        self.spn_cash_received.setToolTip(
            "Enter the cash handed over by the customer." if is_cash
            else "Cash received is only used for cash payments."
        )

    def toggle_pay_method(self):
        idx = (self.cmb_pay_method.currentIndex() + 1) % self.cmb_pay_method.count()
        self.cmb_pay_method.setCurrentIndex(idx)

    def on_search_text_changed(self, text: str):
        now = time.time()
        time_delta = (now - getattr(self, "_last_search_key_time", 0.0)) * 1000
        self._last_search_key_time = now

        self.search_timer.stop()
        term = text.strip()
        if not term:
            self.hide_search_table()
            return

        # Barcode Fast Path Detection (<25ms inter-keystroke timing or barcode length >= 8)
        if (time_delta < 25 and len(term) >= 8) or term.endswith("\n"):
            exact = _POS_CONTROLLER.product_by_barcode(term)
            if exact:
                p_id, p_name, p_price, b_id, b_qty, b_exp = exact
                prod_dict = {"prod_id": p_id, "name": p_name, "price": float(p_price), "batch_id": b_id, "stock": b_qty}
                self.session.add_to_cart(prod_dict, qty=1)
                self.txt_search.clear()
                self.hide_search_table()
                self.refresh_cart_display()
                self.toast.show_message(f"Added {p_name}", ToastType.SUCCESS)
                return

        if time_delta < 30 and len(term) >= 3:
            self.perform_live_search()
        else:
            self.search_timer.start(150)

    def perform_live_search(self):
        term = self.txt_search.text().strip()
        if not term:
            self.hide_search_table()
            return

        results = _POS_CONTROLLER.search_products(term)
        if not results:
            self.hide_search_table()
            return

        self.search_results_data = results
        self.search_catalog_model.update_data(results)
        self.show_search_table()
        self.search_table.selectRow(0)

    def on_search_submit(self):
        self.search_timer.stop()
        term = self.txt_search.text().strip()
        if not term:
            self.hide_search_table()
            return

        # 1. Barcode Fast Path: Exact lookup match
        exact = _POS_CONTROLLER.product_by_barcode(term)
        if exact:
            p_id, p_name, p_price, b_id, b_qty, b_exp = exact
            prod_dict = {"prod_id": p_id, "name": p_name, "price": float(p_price), "batch_id": b_id, "stock": b_qty}
            self.session.add_to_cart(prod_dict, qty=1)
            self.txt_search.clear()
            self.hide_search_table()
            self.refresh_cart_display()
            self.toast.show_message(f"Added {p_name}", ToastType.SUCCESS)
            return

        # 2. If user pressed Enter while search table is visible and has a row selected
        if self.search_table.isVisible() and self.search_table.rowCount() > 0:
            row = self.search_table.currentRow()
            if row < 0:
                row = 0
            self.add_product_from_search_table(row)
            return

        results = _POS_CONTROLLER.search_products(term)
        if not results:
            self.toast.show_message(f"No products found matching '{term}'", ToastType.WARNING)
            self.hide_search_table()
            return

        if len(results) == 1:
            p_id, p_name, p_price, b_id, b_qty, b_exp = results[0]
            prod_dict = {"prod_id": p_id, "name": p_name, "price": float(p_price), "batch_id": b_id, "stock": b_qty}
            self.session.add_to_cart(prod_dict, qty=1)
            self.txt_search.clear()
            self.hide_search_table()
            self.refresh_cart_display()
            self.toast.show_message(f"Added {p_name}", ToastType.SUCCESS)
        else:
            self.search_results_data = results
            self.search_catalog_model.update_data(results)
            self.show_search_table()
            self.search_table.selectRow(0)

    def on_search_input_arrow_down(self) -> bool:
        if self.search_table.isVisible() and self.search_table.rowCount() > 0:
            self.search_table.setFocus()
            self.search_table.selectRow(0)
            return True
        return False

    def hide_search_table(self):
        self.search_results_data = []
        self.search_table.setMinimumHeight(0)
        self.search_table.setMaximumHeight(0)
        self.search_table.hide()

    def show_search_table(self):
        self.search_table.setMinimumHeight(140)
        self.search_table.setMaximumHeight(140)
        self.search_table.show()

    def add_product_from_search_table(self, row: int):
        if 0 <= row < len(self.search_results_data):
            p_id, p_name, p_price, b_id, b_qty, b_exp = self.search_results_data[row]
            prod_dict = {"prod_id": p_id, "name": p_name, "price": float(p_price), "batch_id": b_id, "stock": b_qty}
            self.session.add_to_cart(prod_dict, qty=1)
            self.txt_search.clear()
            self.hide_search_table()
            self.refresh_cart_display()
            self.txt_search.setFocus()
            self.toast.show_message(f"Added {p_name}", ToastType.SUCCESS)

    def on_search_table_double_clicked(self, index):
        self.add_product_from_search_table(index.row())

    def on_cart_cell_changed(self, item):
        if item.column() == 3:  # Quantity column
            try:
                new_qty = int(item.text())
                row = item.row()
                self.session.update_cart_qty(row, new_qty)
                self.refresh_cart_display()
            except ValueError:
                pass

    def on_cart_qty_delta(self, row: int, delta: int):
        """Adjusts quantity for selected cart row via + and - keys."""
        if 0 <= row < len(self.session.active_cart):
            curr_qty = self.session.active_cart[row]["qty"]
            new_qty = curr_qty + delta
            self.session.update_cart_qty(row, new_qty)
            self.refresh_cart_display()
            if 0 <= row < self.cart_table.rowCount():
                self.cart_table.selectRow(row)

    def on_cust_text_changed(self, text: str):
        val = text.strip()
        if not val:
            self.cust_table.hide()
            self.cust_search_data = []
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText("Walk-in customer")
            set_tone(self.lbl_cust_status, "muted")
            return
        self.perform_customer_search()

    def perform_customer_search(self):
        val = self.txt_customer.text().strip()
        if not val:
            self.cust_table.hide()
            return

        custs = _POS_CONTROLLER.search_customers(val)
        if not custs:
            self.cust_table.hide()
            self.cust_search_data = []
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText(f"Customer '{val}' was not found. Add them in Customers to use credit.")
            set_tone(self.lbl_cust_status, "danger", "semibold")
            return

        self.cust_search_data = custs
        self.cust_table.setRowCount(len(custs))
        for row, item in enumerate(custs):
            cnic, fname, lname, email, city = item
            self.cust_table.setItem(row, 0, QTableWidgetItem(f"{fname} {lname}"))
            self.cust_table.setItem(row, 1, QTableWidgetItem(str(cnic)))
            self.cust_table.setItem(row, 2, QTableWidgetItem(str(city)))

        self.cust_table.show()
        self.cust_table.selectRow(0)

    def on_cust_table_double_clicked(self, index):
        row = index.row() if hasattr(index, "row") else int(index)
        if 0 <= row < len(self.cust_search_data):
            cnic, fname, lname, email, city = self.cust_search_data[row]
            debt = _POS_CONTROLLER.customer_total_debt(cnic)
            self.selected_customer_cnic = cnic
            self.is_customer_verified = True
            self.txt_customer.blockSignals(True)
            self.txt_customer.setText(f"{fname} {lname} ({cnic})")
            self.txt_customer.blockSignals(False)
            self.cust_table.hide()
            self.lbl_cust_status.setText(f"{fname} {lname}  •  Due: Rs. {float(debt):.2f}")
            set_tone(self.lbl_cust_status, "accent", "bold")

    def on_customer_lookup(self):
        self.cust_search_timer.stop()
        val = self.txt_customer.text().strip()
        if not val:
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText("Walk-in customer")
            set_tone(self.lbl_cust_status, "muted")
            return

        if self.cust_table.isVisible() and self.cust_table.rowCount() > 0:
            r = self.cust_table.currentRow()
            if r < 0: r = 0
            self.on_cust_table_double_clicked(self.cust_table.model().index(r, 0))
            return

        custs = _POS_CONTROLLER.search_customers(val)
        if custs:
            cnic, fname, lname, email, city = custs[0]
            debt = _POS_CONTROLLER.customer_total_debt(cnic)
            self.selected_customer_cnic = cnic
            self.is_customer_verified = True
            self.lbl_cust_status.setText(f"{fname} {lname}  •  Due: Rs. {float(debt):.2f}")
            set_tone(self.lbl_cust_status, "accent", "bold")
        else:
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText(f"Customer '{val}' was not found. Add them in Customers to use credit.")
            set_tone(self.lbl_cust_status, "danger", "semibold")

    def refresh_cart_display(self):
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(self.session.active_cart))

        for row, item in enumerate(self.session.active_cart):
            self.cart_table.setItem(row, 0, QTableWidgetItem(str(item["name"])))
            self.cart_table.setItem(row, 1, QTableWidgetItem(f"Batch #{item.get('batch_id', '-')}") )
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{item['price']:.2f}"))
            
            qty_item = QTableWidgetItem(str(item["qty"]))
            self.cart_table.setItem(row, 3, qty_item)

            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{item['subtotal']:.2f}"))
            self.cart_table.setItem(row, 5, QTableWidgetItem(str(item.get("stock", "-"))))

        self.cart_table.blockSignals(False)

        # Empty-state visibility
        has_items = self.session.active_cart and len(self.session.active_cart) > 0
        self.lbl_cart_empty.setVisible(not has_items)
        self.cart_table.setVisible(has_items)

        # Update totals (tax preview mirrors the backend's SettingsService rate)
        subtotal = self.session.get_cart_subtotal()
        self.session.discount_amount = self.spn_discount.value()
        net_total = self.session.get_cart_total()

        try:
            tax_rate = float(_POS_CONTROLLER.tax_rate())
            tax_amount = max(0.0, net_total) * tax_rate
            total_with_tax = net_total + tax_amount
        except Exception:
            tax_rate = tax_amount = 0.0
            total_with_tax = net_total

        cash_rec = getattr(self, "spn_cash_received", None)
        cash_val = cash_rec.value() if cash_rec else 0.0
        change_due = max(0.0, cash_val - total_with_tax) if cash_val > 0 else 0.0

        self.lbl_subtotal.setText(f"Subtotal: Rs. {subtotal:.2f}")
        if hasattr(self, "lbl_tax"):
            self.lbl_tax.setText(f"Tax ({tax_rate * 100:.2f}%): Rs. {tax_amount:.2f}")
        self.lbl_total.setText(f"Total: Rs. {total_with_tax:.2f}")
        if hasattr(self, "lbl_change"):
            self.lbl_change.setText(f"Change: Rs. {change_due:.2f}")

    def remove_cart_row(self, row: int):
        self.session.remove_from_cart(row)
        self.refresh_cart_display()
        self.toast.show_message("Item removed", ToastType.INFO)

    def _reset_cart_state(self):
        self.session.clear_cart()
        self.spn_discount.setValue(0.0)
        self.txt_customer.clear()
        self.selected_customer_cnic = None
        self.is_customer_verified = False
        self.lbl_cust_status.setText("Walk-in customer")
        set_tone(self.lbl_cust_status, "muted")
        self.refresh_cart_display()

    def on_clear_cart_requested(self):
        if not self.session.active_cart:
            self.toast.show_message("There are no items to clear.", ToastType.INFO)
            return
        item_count = len(self.session.active_cart)
        self._cart_undo_cache = copy.deepcopy(self.session.active_cart)
        self._reset_cart_state()
        self.toast.show_message(
            f"Cart cleared ({item_count} item{'s' if item_count != 1 else ''} removed)",
            ToastType.INFO,
            duration_ms=4000,
            undo_callback=self._restore_cart_from_undo,
        )

    def on_clear_cart(self):
        self._reset_cart_state()
        self.txt_search.setFocus()

    def _restore_cart_from_undo(self):
        if not self._cart_undo_cache:
            return
        for item in self._cart_undo_cache:
            self.session.add_to_cart(item, qty=item.get("qty", 1))
        self._cart_undo_cache = []
        self.refresh_cart_display()
        self.toast.show_message("Sale restored", ToastType.SUCCESS)

    def on_hold_sale(self):
        if not self.session.active_cart:
            self.toast.show_message("Add at least one item before holding the sale.", ToastType.WARNING)
            return

        emp_id = self.session.current_user.get("id", 1) if self.session.current_user else 1
        cust_id = self.selected_customer_cnic or "WALKIN"
        ok, res = _POS_CONTROLLER.hold_sale(cust_id, emp_id, self.session.active_cart)
        if ok:
            self.toast.show_message(f"Sale #{res} is on hold.", ToastType.SUCCESS)
            self.on_clear_cart()
        else:
            self.toast.show_message(f"Could not hold sale: {res}", ToastType.ERROR)

    def on_recall_sale(self):
        held = _POS_CONTROLLER.held_sales()
        if not held:
            self.toast.show_message("There are no held sales to resume.", ToastType.INFO)
            return

        if len(held) == 1 or not self.show_message_box:
            target_hold_id = held[-1][0]
        else:
            dlg = RecallSaleDialog(held, parent=self)
            if dlg.exec() != QDialog.Accepted or dlg.selected_hold_id is None:
                return
            target_hold_id = dlg.selected_hold_id

        ok, res = _POS_CONTROLLER.recall_sale(target_hold_id)
        if ok and isinstance(res, dict) and "cart" in res:
            self.session.clear_cart()
            for item in res["cart"]:
                self.session.add_to_cart(item, qty=item.get("qty", 1))
            self.refresh_cart_display()
            self.toast.show_message(f"Sale #{target_hold_id} resumed.", ToastType.SUCCESS)
        else:
            self.toast.show_message(f"Could not resume sale: {res}", ToastType.ERROR)
        self.txt_search.setFocus()

    def on_checkout(self):
        if self._checkout_in_progress:
            return

        if not self.session.active_cart:
            self.toast.show_message("Add at least one item before completing the sale.", ToastType.WARNING)
            return

        cust_id = self.selected_customer_cnic or "WALKIN"
        emp_id = self.session.current_user.get("id", 1) if self.session.current_user else 1

        # Check Active Cash Register Shift Session
        active_sess = _POS_CONTROLLER.active_session(emp_id)
        if not active_sess and self.show_message_box:
            from ui.screens.cash_session_screen import OpenSessionDialog
            dlg = OpenSessionDialog(emp_id, parent=self)
            if dlg.exec() != QDialog.Accepted:
                self.toast.show_message("Open your cash shift before completing a sale.", ToastType.WARNING)
                return

        pay_method = self.cmb_pay_method.currentData() or self.cmb_pay_method.currentText()
        discount = self.spn_discount.value()

        # Manager gate: discounts above the cashier threshold require approval
        if discount > 0:
            subtotal = self.session.get_cart_subtotal()
            if subtotal > 0 and (discount / subtotal) * 100.0 > _POS_CONTROLLER.discount_threshold_pct:
                from ui.widgets.manager_auth_modal import ManagerAuthModal
                dlg = ManagerAuthModal(discount, subtotal, parent=self)
                if dlg.exec() != QDialog.Accepted or not dlg.authorized_by:
                    self.toast.show_message("Manager approval is required for this discount.", ToastType.WARNING)
                    return

        if pay_method == "Khatoo Credit":
            if not self.selected_customer_cnic or not self.is_customer_verified:
                self.toast.show_message("Select a registered customer before using customer credit.", ToastType.ERROR)
                return

        req = _POS_CONTROLLER.checkout_request(
            customer_id=cust_id,
            employee_id=emp_id,
            cart=self.session.active_cart,
            discount=discount,
            payment_method=pay_method,
            total=self.session.get_cart_total()
        )

        # Loading state & Re-entrancy guard
        self._checkout_in_progress = True
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setText("Completing sale…")
        self.btn_checkout.setCursor(Qt.WaitCursor)
        if hasattr(self, "sc_f10"): self.sc_f10.setEnabled(False)
        if hasattr(self, "sc_f12"): self.sc_f12.setEnabled(False)

        try:
            result = _POS_CONTROLLER.process_checkout(req)
        finally:
            self._checkout_in_progress = False
            self.btn_checkout.setEnabled(True)
            self.btn_checkout.setText("Complete Sale (F10)")
            self.btn_checkout.setCursor(Qt.ArrowCursor)
            if hasattr(self, "sc_f10"): self.sc_f10.setEnabled(True)
            if hasattr(self, "sc_f12"): self.sc_f12.setEnabled(True)

        if result.success:
            self.toast.show_message(f"Sale completed. {result.message}", ToastType.SUCCESS)
            self.on_clear_cart()
        else:
            self.toast.show_message(f"Sale could not be completed: {result.message}", ToastType.ERROR)
        self.txt_search.setFocus()

