"""Fast, keyboard-friendly pharmacy counter screen for Pharma-Khaato."""

import copy
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDoubleSpinBox,
    QFrame, QDialog, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.toast import Toast, ToastType
from ui.widgets.pos_models import ProductCatalogModel
from ui.widgets.responsive import flexible_side_panel
from ui.widgets.semantic_style import set_tone
from ui.widgets.pos_widgets import (
    SearchLineEdit, SearchResultsTable, CartTableWidget, RecallSaleDialog,
)
from ui.widgets.table_polish import polish_table
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
        self.cust_search_data = []
        self._checkout_in_progress = False
        self._last_search_key_time = 0.0
        self.search_catalog_model = ProductCatalogModel(self)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_live_search)

        self.cust_search_timer = QTimer(self)
        self.cust_search_timer.setSingleShot(True)
        self.cust_search_timer.timeout.connect(self.perform_customer_search)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        search_card = Card()
        search_layout = search_card.layout()
        search_layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("New Sale")
        title.setObjectName("h1")
        title.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 800;")
        header.addWidget(title)
        header.addStretch()

        shortcut_hint = QLabel("F1 search  •  F2 customer  •  F10 complete")
        shortcut_hint.setObjectName("caption")
        shortcut_hint.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        shortcut_hint.setToolTip(
            "Keyboard shortcuts: F1 product search, F2 customer, F3 discount, "
            "F4 payment method, F5 hold, F6 held sales, F10/F12 complete sale."
        )
        header.addWidget(shortcut_hint)
        search_layout.addLayout(header)

        self.txt_search = SearchLineEdit(
            on_down_callback=self.on_search_input_arrow_down,
            on_escape_callback=self.hide_search_table,
        )
        self.txt_search.setPlaceholderText("Scan barcode or search product name / formula")
        self.txt_search.setAccessibleName("Find product")
        self.txt_search.setAccessibleDescription(
            "Scan a barcode or type a product name or formula."
        )
        self.txt_search.setObjectName("primarySearch")
        self.txt_search.textChanged.connect(self.on_search_text_changed)
        self.txt_search.returnPressed.connect(self.on_search_submit)
        search_layout.addWidget(self.txt_search)

        self.lbl_search_feedback = QLabel()
        self.lbl_search_feedback.setObjectName("caption")
        self.lbl_search_feedback.setWordWrap(True)
        self.lbl_search_feedback.hide()
        search_layout.addWidget(self.lbl_search_feedback)

        left_col.addWidget(search_card)

        self.search_table = SearchResultsTable(
            on_select_callback=self.add_product_from_search_table,
            on_cancel_callback=self.hide_search_table,
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

        cart_card = Card()
        cart_layout = cart_card.layout()

        cart_header = QLabel("Sale Items")
        cart_header.setObjectName("h2")
        cart_layout.addWidget(cart_header)

        self.cart_table = CartTableWidget(
            on_delete_callback=self.remove_cart_row,
            on_qty_change_callback=self.on_cart_qty_delta,
        )
        self.cart_table.setAccessibleName("Items in this sale")
        self.cart_table.setToolTip(
            "Select an item and press Delete to remove it. Use + or - to change quantity."
        )
        self.cart_table.setHorizontalHeaderLabels(
            ["Product", "Batch", "Price", "Qty", "Amount", "In Stock"]
        )
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.itemChanged.connect(self.on_cart_cell_changed)
        polish_table(self.cart_table)

        self.lbl_cart_empty = QLabel("No items yet — scan a barcode or search for a product")
        self.lbl_cart_empty.setAlignment(Qt.AlignCenter)
        self.lbl_cart_empty.setObjectName("emptyState")
        self.lbl_cart_empty.setWordWrap(True)

        cart_layout.addWidget(self.cart_table)
        cart_layout.addWidget(self.lbl_cart_empty)
        left_col.addWidget(cart_card, 1)

        right_card = Card()
        flexible_side_panel(right_card, minimum=292, maximum=420)
        right_layout = right_card.layout()
        right_layout.setSpacing(12)

        # Persistent error-prevention cue: counter staff should know about a
        # closed shift before they reach the final checkout click.
        self.shift_banner = QFrame()
        self.shift_banner.setObjectName("insetPanel")
        shift_layout = QHBoxLayout(self.shift_banner)
        shift_layout.setContentsMargins(10, 8, 10, 8)
        shift_layout.setSpacing(8)

        self.lbl_shift_notice = QLabel("No shift open — start a cash shift before completing sales.")
        self.lbl_shift_notice.setWordWrap(True)
        set_tone(self.lbl_shift_notice, "warning", "semibold")
        shift_layout.addWidget(self.lbl_shift_notice, 1)

        self.btn_start_shift = QPushButton("Start Shift")
        self.btn_start_shift.setObjectName("successButton")
        self.btn_start_shift.setProperty("compact", True)
        self.btn_start_shift.clicked.connect(self._start_shift_from_pos)
        shift_layout.addWidget(self.btn_start_shift)
        right_layout.addWidget(self.shift_banner)

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

        customer_label = QLabel("Customer (optional):")
        self.txt_customer = QLineEdit()
        self.txt_customer.setPlaceholderText("Walk-in — search name or CNIC")
        self.txt_customer.setAccessibleName("Find customer")
        self.txt_customer.textChanged.connect(self.on_cust_text_changed)
        self.txt_customer.editingFinished.connect(self.on_customer_lookup)
        summary_layout.addWidget(customer_label)
        summary_layout.addWidget(self.txt_customer)

        self.cust_table = QTableWidget(0, 3)
        self.cust_table.setHorizontalHeaderLabels(["Name", "CNIC", "Area"])
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

        self.lbl_cust_status = QLabel("Walk-in customer")
        self.lbl_cust_status.setWordWrap(True)
        set_tone(self.lbl_cust_status, "muted")
        summary_layout.addWidget(self.lbl_cust_status)
        summary_layout.addSpacing(4)

        payment_label = QLabel("Pay with:")
        self.cmb_pay_method = QComboBox()
        for display_label, backend_value in PAYMENT_OPTIONS:
            self.cmb_pay_method.addItem(display_label, backend_value)
        self.cmb_pay_method.setAccessibleName("Payment method")
        self.cmb_pay_method.setToolTip(
            "Customer Credit requires a registered customer."
        )
        self.cmb_pay_method.currentIndexChanged.connect(self._on_payment_method_changed)
        summary_layout.addWidget(payment_label)
        summary_layout.addWidget(self.cmb_pay_method)
        summary_layout.addSpacing(4)

        fin_frame = QFrame()
        fin_frame.setObjectName("insetPanel")
        fin_layout = QVBoxLayout(fin_frame)

        self.lbl_subtotal = QLabel("Subtotal: Rs. 0.00")
        set_tone(self.lbl_subtotal, "primary", "bold")

        discount_row = QHBoxLayout()
        discount_row.addWidget(QLabel("Discount:"))
        self.spn_discount = QDoubleSpinBox()
        self.spn_discount.setRange(0.0, 100000.0)
        self.spn_discount.setPrefix("Rs. ")
        self.spn_discount.setDecimals(2)
        self.spn_discount.setAccessibleName("Discount amount")
        self.spn_discount.valueChanged.connect(self.refresh_cart_display)
        discount_row.addWidget(self.spn_discount)

        cash_row = QHBoxLayout()
        self.lbl_cash_received = QLabel("Cash received:")
        cash_row.addWidget(self.lbl_cash_received)
        self.spn_cash_received = QDoubleSpinBox()
        self.spn_cash_received.setRange(0.0, 1000000.0)
        self.spn_cash_received.setPrefix("Rs. ")
        self.spn_cash_received.setDecimals(2)
        self.spn_cash_received.setAccessibleName("Cash received")
        self.spn_cash_received.valueChanged.connect(self.refresh_cart_display)
        cash_row.addWidget(self.spn_cash_received)

        self.lbl_total = QLabel("Total: Rs. 0.00")
        self.lbl_total.setObjectName("posTotal")
        self.lbl_total.setWordWrap(True)

        self.lbl_tax = QLabel("Tax: Rs. 0.00")
        set_tone(self.lbl_tax, "secondary", "bold")

        self.lbl_change = QLabel("Change: Rs. 0.00")
        set_tone(self.lbl_change, "success", "bold")

        fin_layout.addWidget(self.lbl_subtotal)
        fin_layout.addLayout(discount_row)
        fin_layout.addLayout(cash_row)
        fin_layout.addSpacing(8)
        fin_layout.addWidget(self.lbl_tax)
        fin_layout.addWidget(self.lbl_total)
        fin_layout.addWidget(self.lbl_change)
        summary_layout.addWidget(fin_frame)
        summary_layout.addStretch()
        right_layout.addWidget(summary_scroll, 1)

        self.btn_checkout = QPushButton("Complete Sale")
        self.btn_checkout.setObjectName("primaryButton")
        self.btn_checkout.setAccessibleName("Complete sale")
        self.btn_checkout.setToolTip("Complete this sale (F10 or F12)")
        self.btn_checkout.setMinimumHeight(44)
        self.btn_checkout.clicked.connect(self.on_checkout)

        hold_row = QHBoxLayout()
        self.btn_hold = QPushButton("Hold Sale")
        self.btn_hold.setToolTip("Hold this sale (F5)")
        self.btn_hold.clicked.connect(self.on_hold_sale)
        self.btn_recall = QPushButton("Held Sales")
        self.btn_recall.setToolTip("Resume a held sale (F6)")
        self.btn_recall.clicked.connect(self.on_recall_sale)
        hold_row.addWidget(self.btn_hold)
        hold_row.addWidget(self.btn_recall)

        self.btn_clear = QPushButton("Clear Sale")
        self.btn_clear.setToolTip("Clear the sale (Ctrl+Delete)")
        self.btn_clear.clicked.connect(self.on_clear_cart_requested)

        right_layout.addWidget(self.btn_checkout)
        right_layout.addLayout(hold_row)
        right_layout.addWidget(self.btn_clear)

        layout.addLayout(left_col, 7)
        layout.addWidget(right_card, 3)
        layout.setStretch(0, 7)
        layout.setStretch(1, 3)

        self.toast = Toast(self)
        self.setup_hotkeys()
        self._on_payment_method_changed()
        self._refresh_shift_state()
        self.refresh_cart_display()

    def on_screen_show(self):
        self._refresh_shift_state()
        self.txt_search.setFocus()

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
        self.sc_clear = QShortcut(
            QKeySequence("Ctrl+Delete"), self, activated=self.on_clear_cart_requested
        )

    def _current_employee_id(self) -> int:
        user = self.session.current_user
        return int(user.get("id", 1)) if user else 1

    def _refresh_shift_state(self) -> bool:
        try:
            is_open = bool(_POS_CONTROLLER.active_session(self._current_employee_id()))
        except Exception:
            is_open = False
        self.shift_banner.setVisible(not is_open)
        return is_open

    def _start_shift_from_pos(self):
        from ui.screens.cash_session_screen import OpenSessionDialog

        dialog = OpenSessionDialog(self._current_employee_id(), parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._refresh_shift_state()
            self.txt_search.setFocus()

    def _set_search_feedback(self, text: str = "", tone: str = "muted"):
        self.lbl_search_feedback.setText(text)
        self.lbl_search_feedback.setVisible(bool(text))
        if text:
            set_tone(self.lbl_search_feedback, tone, "semibold" if tone == "danger" else None)

    def _on_escape(self):
        if self.search_table.isVisible():
            self.hide_search_table()
        elif self.txt_search.hasFocus():
            self.txt_search.clear()
            self.txt_search.clearFocus()

    def _on_payment_method_changed(self, *_):
        is_cash = (
            self.cmb_pay_method.currentData() or self.cmb_pay_method.currentText()
        ) == "Cash"
        self.spn_cash_received.setEnabled(is_cash)
        self.lbl_cash_received.setEnabled(is_cash)
        if not is_cash and self.spn_cash_received.value() != 0.0:
            self.spn_cash_received.setValue(0.0)
        self.spn_cash_received.setToolTip(
            "Enter cash handed over to calculate change. Leave at Rs. 0.00 for exact cash."
            if is_cash
            else "Cash received is only used for cash payments."
        )

    def toggle_pay_method(self):
        index = (self.cmb_pay_method.currentIndex() + 1) % self.cmb_pay_method.count()
        self.cmb_pay_method.setCurrentIndex(index)

    def on_search_text_changed(self, text: str):
        now = time.time()
        time_delta = (now - self._last_search_key_time) * 1000
        self._last_search_key_time = now

        self.search_timer.stop()
        term = text.strip()
        if not term:
            self.hide_search_table(clear_feedback=True)
            return

        self._set_search_feedback()

        if (time_delta < 25 and len(term) >= 8) or term.endswith("\n"):
            exact = _POS_CONTROLLER.product_by_barcode(term)
            if exact:
                self._add_result_tuple_to_cart(exact)
                return

        if time_delta < 30 and len(term) >= 3:
            self.perform_live_search()
        else:
            self.search_timer.start(150)

    def perform_live_search(self):
        term = self.txt_search.text().strip()
        if not term:
            self.hide_search_table(clear_feedback=True)
            return

        results = _POS_CONTROLLER.search_products(term)
        if not results:
            self.hide_search_table()
            self._set_search_feedback(
                "No matching sellable stock. Try a product name, formula, or barcode.",
                "danger",
            )
            return

        self._set_search_feedback()
        self.search_results_data = results
        self.search_catalog_model.update_data(results)
        self.show_search_table()
        self.search_table.selectRow(0)

    def on_search_submit(self):
        self.search_timer.stop()
        term = self.txt_search.text().strip()
        if not term:
            self.hide_search_table(clear_feedback=True)
            return

        exact = _POS_CONTROLLER.product_by_barcode(term)
        if exact:
            self._add_result_tuple_to_cart(exact)
            return

        if self.search_table.isVisible() and self.search_table.rowCount() > 0:
            row = max(0, self.search_table.currentRow())
            self.add_product_from_search_table(row)
            return

        results = _POS_CONTROLLER.search_products(term)
        if not results:
            self.hide_search_table()
            self._set_search_feedback(
                "No matching sellable stock. Check the spelling, barcode, or Stock & Products.",
                "danger",
            )
            self.toast.show_message("No sellable product found.", ToastType.WARNING)
            return

        if len(results) == 1:
            self._add_result_tuple_to_cart(results[0])
        else:
            self._set_search_feedback()
            self.search_results_data = results
            self.search_catalog_model.update_data(results)
            self.show_search_table()
            self.search_table.selectRow(0)

    def _add_result_tuple_to_cart(self, result):
        product_id, product_name, price, batch_id, batch_qty, _batch_expiry = result
        product = {
            "prod_id": product_id,
            "name": product_name,
            "price": float(price),
            "batch_id": batch_id,
            "stock": batch_qty,
        }
        self.session.add_to_cart(product, qty=1)
        self.txt_search.clear()
        self.hide_search_table(clear_feedback=True)
        self.refresh_cart_display()
        self.txt_search.setFocus()
        self.toast.show_message(f"Added {product_name}", ToastType.SUCCESS)

    def on_search_input_arrow_down(self) -> bool:
        if self.search_table.isVisible() and self.search_table.rowCount() > 0:
            self.search_table.setFocus()
            self.search_table.selectRow(0)
            return True
        return False

    def hide_search_table(self, clear_feedback: bool = False):
        self.search_results_data = []
        self.search_table.setMinimumHeight(0)
        self.search_table.setMaximumHeight(0)
        self.search_table.hide()
        if clear_feedback:
            self._set_search_feedback()

    def show_search_table(self):
        self.search_table.setMinimumHeight(140)
        self.search_table.setMaximumHeight(140)
        self.search_table.show()

    def add_product_from_search_table(self, row: int):
        if 0 <= row < len(self.search_results_data):
            self._add_result_tuple_to_cart(self.search_results_data[row])

    def on_search_table_double_clicked(self, index):
        self.add_product_from_search_table(index.row())

    def on_cart_cell_changed(self, item):
        if item.column() != 3:
            return
        try:
            self.session.update_cart_qty(item.row(), int(item.text()))
            self.refresh_cart_display()
        except ValueError:
            self.refresh_cart_display()

    def on_cart_qty_delta(self, row: int, delta: int):
        if 0 <= row < len(self.session.active_cart):
            current = self.session.active_cart[row]["qty"]
            self.session.update_cart_qty(row, current + delta)
            self.refresh_cart_display()
            if 0 <= row < self.cart_table.rowCount():
                self.cart_table.selectRow(row)

    def on_cust_text_changed(self, text: str):
        value = text.strip()
        if not value:
            self.cust_table.hide()
            self.cust_search_data = []
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText("Walk-in customer")
            set_tone(self.lbl_cust_status, "muted")
            return
        self.cust_search_timer.stop()
        self.cust_search_timer.start(120)

    def perform_customer_search(self):
        value = self.txt_customer.text().strip()
        if not value:
            self.cust_table.hide()
            return

        customers = _POS_CONTROLLER.search_customers(value)
        if not customers:
            self.cust_table.hide()
            self.cust_search_data = []
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText(
                "Customer not found. Add them in Customers before using customer credit."
            )
            set_tone(self.lbl_cust_status, "danger", "semibold")
            return

        self.cust_search_data = customers
        self.cust_table.setRowCount(len(customers))
        for row, item in enumerate(customers):
            cnic, first_name, last_name, _email, city = item
            self.cust_table.setItem(
                row, 0, QTableWidgetItem(f"{first_name} {last_name}".strip())
            )
            self.cust_table.setItem(row, 1, QTableWidgetItem(str(cnic)))
            self.cust_table.setItem(row, 2, QTableWidgetItem(str(city)))

        self.cust_table.show()
        self.cust_table.selectRow(0)

    def on_cust_table_double_clicked(self, index):
        row = index.row() if hasattr(index, "row") else int(index)
        if 0 <= row < len(self.cust_search_data):
            cnic, first_name, last_name, _email, _city = self.cust_search_data[row]
            debt = _POS_CONTROLLER.customer_total_debt(cnic)
            self.selected_customer_cnic = cnic
            self.is_customer_verified = True
            self.txt_customer.blockSignals(True)
            self.txt_customer.setText(f"{first_name} {last_name} ({cnic})")
            self.txt_customer.blockSignals(False)
            self.cust_table.hide()
            self.lbl_cust_status.setText(
                f"{first_name} {last_name}  •  Due: Rs. {float(debt):.2f}"
            )
            set_tone(self.lbl_cust_status, "accent", "bold")

    def on_customer_lookup(self):
        self.cust_search_timer.stop()
        value = self.txt_customer.text().strip()
        if not value:
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText("Walk-in customer")
            set_tone(self.lbl_cust_status, "muted")
            return

        if self.cust_table.isVisible() and self.cust_table.rowCount() > 0:
            row = max(0, self.cust_table.currentRow())
            self.on_cust_table_double_clicked(self.cust_table.model().index(row, 0))
            return

        customers = _POS_CONTROLLER.search_customers(value)
        if customers:
            cnic, first_name, last_name, _email, _city = customers[0]
            debt = _POS_CONTROLLER.customer_total_debt(cnic)
            self.selected_customer_cnic = cnic
            self.is_customer_verified = True
            self.lbl_cust_status.setText(
                f"{first_name} {last_name}  •  Due: Rs. {float(debt):.2f}"
            )
            set_tone(self.lbl_cust_status, "accent", "bold")
        else:
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText(
                "Customer not found. Add them in Customers before using customer credit."
            )
            set_tone(self.lbl_cust_status, "danger", "semibold")

    def refresh_cart_display(self):
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(self.session.active_cart))

        for row, item in enumerate(self.session.active_cart):
            self.cart_table.setItem(row, 0, QTableWidgetItem(str(item["name"])))
            # Batch stays in the table for internal traceability but is hidden by
            # the shared table policy on routine screens.
            self.cart_table.setItem(
                row, 1, QTableWidgetItem(str(item.get("batch_id", "-")))
            )
            self.cart_table.setItem(
                row, 2, QTableWidgetItem(f"Rs. {float(item['price']):.2f}")
            )
            self.cart_table.setItem(row, 3, QTableWidgetItem(str(item["qty"])))
            self.cart_table.setItem(
                row, 4, QTableWidgetItem(f"Rs. {float(item['subtotal']):.2f}")
            )
            self.cart_table.setItem(
                row, 5, QTableWidgetItem(str(item.get("stock", "-")))
            )

        self.cart_table.blockSignals(False)

        has_items = bool(self.session.active_cart)
        self.lbl_cart_empty.setVisible(not has_items)
        self.cart_table.setVisible(has_items)

        subtotal = self.session.get_cart_subtotal()
        self.session.discount_amount = self.spn_discount.value()
        net_total = self.session.get_cart_total()

        try:
            tax_rate = float(_POS_CONTROLLER.tax_rate())
            tax_amount = max(0.0, net_total) * tax_rate
            total_with_tax = net_total + tax_amount
        except Exception:
            tax_rate = 0.0
            tax_amount = 0.0
            total_with_tax = net_total

        cash_value = self.spn_cash_received.value()
        change_due = max(0.0, cash_value - total_with_tax) if cash_value > 0 else 0.0

        self.lbl_subtotal.setText(f"Subtotal: Rs. {subtotal:.2f}")
        self.lbl_tax.setText(f"Tax ({tax_rate * 100:.2f}%): Rs. {tax_amount:.2f}")
        self.lbl_total.setText(f"Total: Rs. {total_with_tax:.2f}")
        self.lbl_change.setText(f"Change: Rs. {change_due:.2f}")

    def remove_cart_row(self, row: int):
        self.session.remove_from_cart(row)
        self.refresh_cart_display()
        self.toast.show_message("Item removed", ToastType.INFO)

    def _reset_cart_state(self):
        self.session.clear_cart()
        self.spn_discount.setValue(0.0)
        self.spn_cash_received.setValue(0.0)
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
            f"Sale cleared ({item_count} item{'s' if item_count != 1 else ''} removed)",
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
            self.toast.show_message(
                "Add at least one item before holding the sale.", ToastType.WARNING
            )
            return

        employee_id = self._current_employee_id()
        customer_id = self.selected_customer_cnic or "WALKIN"
        ok, result = _POS_CONTROLLER.hold_sale(
            customer_id, employee_id, self.session.active_cart
        )
        if ok:
            self.toast.show_message("Sale held for later.", ToastType.SUCCESS)
            self.on_clear_cart()
        else:
            self.toast.show_message(f"Could not hold sale: {result}", ToastType.ERROR)

    def on_recall_sale(self):
        held = _POS_CONTROLLER.held_sales()
        if not held:
            self.toast.show_message("There are no held sales to resume.", ToastType.INFO)
            return

        if len(held) == 1 or not self.show_message_box:
            hold_id = held[-1][0]
        else:
            dialog = RecallSaleDialog(held, parent=self)
            if dialog.exec() != QDialog.Accepted or dialog.selected_hold_id is None:
                return
            hold_id = dialog.selected_hold_id

        ok, result = _POS_CONTROLLER.recall_sale(hold_id)
        if ok and isinstance(result, dict) and "cart" in result:
            self.session.clear_cart()
            for item in result["cart"]:
                self.session.add_to_cart(item, qty=item.get("qty", 1))
            self.refresh_cart_display()
            self.toast.show_message("Held sale resumed.", ToastType.SUCCESS)
        else:
            self.toast.show_message(f"Could not resume sale: {result}", ToastType.ERROR)
        self.txt_search.setFocus()

    def on_checkout(self):
        if self._checkout_in_progress:
            return
        if not self.session.active_cart:
            self.toast.show_message(
                "Add at least one item before completing the sale.", ToastType.WARNING
            )
            return

        employee_id = self._current_employee_id()
        if not _POS_CONTROLLER.active_session(employee_id):
            self._refresh_shift_state()
            if self.show_message_box:
                self._start_shift_from_pos()
            if not _POS_CONTROLLER.active_session(employee_id):
                self.toast.show_message(
                    "Start a cash shift before completing sales.", ToastType.WARNING
                )
                return

        customer_id = self.selected_customer_cnic or "WALKIN"
        payment_method = self.cmb_pay_method.currentData() or self.cmb_pay_method.currentText()
        discount = self.spn_discount.value()

        if discount > self.session.get_cart_subtotal():
            self.toast.show_message(
                "Discount cannot be greater than the sale subtotal.", ToastType.WARNING
            )
            return

        if discount > 0:
            subtotal = self.session.get_cart_subtotal()
            if subtotal > 0 and (
                (discount / subtotal) * 100.0 > _POS_CONTROLLER.discount_threshold_pct
            ):
                from ui.widgets.manager_auth_modal import ManagerAuthModal

                dialog = ManagerAuthModal(discount, subtotal, parent=self)
                if dialog.exec() != QDialog.Accepted or not dialog.authorized_by:
                    self.toast.show_message(
                        "Manager approval is required for this discount.",
                        ToastType.WARNING,
                    )
                    return

        if payment_method == "Khatoo Credit":
            if not self.selected_customer_cnic or not self.is_customer_verified:
                self.toast.show_message(
                    "Select a registered customer before using customer credit.",
                    ToastType.ERROR,
                )
                return

        request = _POS_CONTROLLER.checkout_request(
            customer_id=customer_id,
            employee_id=employee_id,
            cart=self.session.active_cart,
            discount=discount,
            payment_method=payment_method,
            total=self.session.get_cart_total(),
        )

        self._checkout_in_progress = True
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setText("Completing sale…")
        self.btn_checkout.setCursor(Qt.WaitCursor)
        self.sc_f10.setEnabled(False)
        self.sc_f12.setEnabled(False)

        try:
            result = _POS_CONTROLLER.process_checkout(request)
        finally:
            self._checkout_in_progress = False
            self.btn_checkout.setEnabled(True)
            self.btn_checkout.setText("Complete Sale")
            self.btn_checkout.setCursor(Qt.ArrowCursor)
            self.sc_f10.setEnabled(True)
            self.sc_f12.setEnabled(True)

        if result.success:
            self.toast.show_message("Sale completed successfully.", ToastType.SUCCESS)
            self.on_clear_cart()
            self._refresh_shift_state()
        else:
            self.toast.show_message(
                f"Sale could not be completed: {result.message}", ToastType.ERROR
            )
        self.txt_search.setFocus()
