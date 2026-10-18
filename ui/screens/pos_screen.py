"""Fast, keyboard-friendly pharmacy counter screen for Pharma-Khaato."""

import copy
from types import SimpleNamespace
from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDoubleSpinBox,
    QFrame, QDialog, QScrollArea, QCheckBox, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QEvent
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
from ui.app.async_tasks import AsyncTaskRunner
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
        self._tasks = AsyncTaskRunner(self)
        self._search_term = None
        self._customer_search_term = None
        self._cash_shift_open = False
        self._tax_rate = 0.0
        self._tax_ready = False
        self._pending_retry_ready = False
        self._last_sale_id = None
        self._sale_generation = 0
        self._submitted_terms = []
        self._product_submit_active = False
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
        self.txt_search.setPlaceholderText("Scan a barcode or type the medicine name")
        self.txt_search.setAccessibleName("Find product")
        self.txt_search.setAccessibleDescription(
            "Scan a barcode or type a medicine name or ingredient."
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
            ["Product", "Batch", "Price", "Qty", "Amount", "In Stock", "Unit"]
        )
        self.cart_table.setColumnCount(7)
        self.cart_table.setHorizontalHeaderLabels(
            ["Product", "Batch", "Price", "Qty", "Amount", "In Stock", "Unit"]
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
        self.txt_customer.setPlaceholderText("For credit: search name or phone")
        self.txt_customer.setAccessibleName("Find customer")
        self.txt_customer.textChanged.connect(self.on_cust_text_changed)
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
        self.cust_table.installEventFilter(self)
        summary_layout.addWidget(self.cust_table)
        self.txt_customer.returnPressed.connect(self.on_customer_lookup)

        self.btn_add_customer = QPushButton("Add Credit Customer")
        self.btn_add_customer.setToolTip("Add a customer without leaving this sale")
        self.btn_add_customer.clicked.connect(self._quick_add_customer)
        summary_layout.addWidget(self.btn_add_customer)

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
        self.chk_exact_cash = QCheckBox("Exact Cash")
        self.chk_exact_cash.setChecked(True)
        self.chk_exact_cash.setToolTip("The customer pays exactly the amount due")
        self.chk_exact_cash.toggled.connect(self._on_payment_method_changed)
        fin_layout.addWidget(self.chk_exact_cash)
        fin_layout.addLayout(cash_row)
        fin_layout.addSpacing(8)
        fin_layout.addWidget(self.lbl_tax)
        fin_layout.addWidget(self.lbl_total)
        fin_layout.addWidget(self.lbl_change)
        summary_layout.addWidget(fin_frame)
        self.lbl_checkout_state = QLabel()
        self.lbl_checkout_state.setWordWrap(True)
        self.lbl_checkout_state.hide()
        summary_layout.addWidget(self.lbl_checkout_state)
        self.last_sale_frame = QFrame()
        last_sale_layout = QVBoxLayout(self.last_sale_frame)
        self.lbl_last_sale = QLabel()
        self.lbl_last_sale.setWordWrap(True)
        last_sale_layout.addWidget(self.lbl_last_sale)
        self.btn_reprint = QPushButton("Reprint Last Receipt")
        self.btn_reprint.clicked.connect(self._reprint_last_sale)
        last_sale_layout.addWidget(self.btn_reprint)
        self.last_sale_frame.hide()
        summary_layout.addWidget(self.last_sale_frame)
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
        self._restore_pending_checkout()

    def on_screen_show(self):
        self._refresh_shift_state()
        self._restore_pending_checkout()
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

    def _current_employee_id(self) -> int | None:
        user = self.session.current_user
        return int(user["id"]) if user and user.get("id") is not None else None

    def _refresh_shift_state(self) -> bool:
        employee_id = self._current_employee_id()
        if employee_id is None:
            return False
        def loaded(payload):
            if self._current_employee_id() != employee_id:
                return
            self._cash_shift_open, self._tax_rate = payload
            self._tax_ready = True
            self.shift_banner.setVisible(not self._cash_shift_open)
            self.refresh_cart_display()
        self._tasks.run_latest(
            "counter-state",
            lambda: (bool(_POS_CONTROLLER.active_session(employee_id)), float(_POS_CONTROLLER.tax_rate())),
            loaded,
            lambda _details: self._set_checkout_notice("Could not check shift and tax settings. Try opening New Sale again.", "danger"),
        )
        return self._cash_shift_open

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
        exact = self.chk_exact_cash.isChecked()
        self.spn_cash_received.setEnabled(is_cash and not exact)
        self.lbl_cash_received.setEnabled(is_cash and not exact)
        self.chk_exact_cash.setVisible(is_cash)
        self.spn_cash_received.setVisible(is_cash)
        self.lbl_cash_received.setVisible(is_cash)
        self.lbl_change.setVisible(is_cash)
        self.btn_add_customer.setVisible((self.cmb_pay_method.currentData() or "") == "Khatoo Credit")
        if not is_cash and self.spn_cash_received.value() != 0.0:
            self.spn_cash_received.setValue(0.0)
        self.spn_cash_received.setToolTip(
            "Untick Exact Cash and enter the amount handed over to calculate change."
            if is_cash
            else "Cash received is only used for cash payments."
        )

    def toggle_pay_method(self):
        index = (self.cmb_pay_method.currentIndex() + 1) % self.cmb_pay_method.count()
        self.cmb_pay_method.setCurrentIndex(index)

    def on_search_text_changed(self, text: str):
        self.search_timer.stop()
        self._tasks.invalidate("product-search")
        self._search_term = None
        self.hide_search_table(clear_feedback=True)
        term = text.strip()
        if not term:
            return
        # Timing must never select medicine: EAN-8 can prefix EAN-13. Only a
        # completed scanner terminator (Return) or explicit result adds stock.
        self.search_timer.start(150)

    def perform_live_search(self):
        term = self.txt_search.text().strip()
        if not term:
            self.hide_search_table(clear_feedback=True)
            return

        self._set_search_feedback("Finding products…")
        self._tasks.run_latest(
            "product-search", lambda: _POS_CONTROLLER.search_products(term),
            lambda results: self._apply_product_search(term, results),
            lambda _details: self._set_search_feedback("Could not search stock. Try again.", "danger"),
        )

    def _apply_product_search(self, term, results, add_single=False):
        if self.txt_search.text().strip() != term or self.session.pending_checkout:
            return
        self._search_term = term
        if not results:
            self.hide_search_table()
            self._set_search_feedback("No matching sellable stock. Check the name or barcode.", "danger")
            return
        if add_single and len(results) == 1:
            self._add_result_tuple_to_cart(results[0])
            return
        self._set_search_feedback()
        self.search_results_data = list(results)
        self.search_catalog_model.update_data(results)
        self.show_search_table()
        self.search_table.selectRow(0)

    def on_search_submit(self):
        if self.session.pending_checkout:
            return
        self.search_timer.stop()
        term = self.txt_search.text().strip()
        if not term:
            self.hide_search_table(clear_feedback=True)
            return

        if (self._search_term == term and self.search_table.isVisible()
                and self.search_table.rowCount() > 0):
            row = max(0, self.search_table.currentRow())
            self.add_product_from_search_table(row)
            return

        # Empty the scanner buffer at its terminator, not at an asynchronous
        # lookup result. Several fast scans must each survive a slow disk read.
        self.txt_search.clear()
        self._submitted_terms.append((term, self._sale_generation, self._current_employee_id()))
        self._resolve_next_submitted_term()

    def _resolve_next_submitted_term(self):
        if self._product_submit_active or not self._submitted_terms:
            return
        term, generation, employee_id = self._submitted_terms.pop(0)
        self._product_submit_active = True
        self._set_search_feedback("Finding scanned product…")
        def resolve():
            exact = _POS_CONTROLLER.product_by_barcode(term)
            return [exact] if exact else _POS_CONTROLLER.search_products(term)
        def complete(results):
            self._product_submit_active = False
            if (generation == self._sale_generation and employee_id == self._current_employee_id()
                    and not self.session.pending_checkout):
                if len(results or []) == 1:
                    self._add_result_tuple_to_cart(results[0], clear_search=False)
                    self._set_search_feedback()
                elif not self.txt_search.text():
                    self.txt_search.blockSignals(True)
                    self.txt_search.setText(term)
                    self.txt_search.blockSignals(False)
                    self._apply_product_search(term, results)
            self._resolve_next_submitted_term()
        def failed(_details):
            self._product_submit_active = False
            self._set_search_feedback(f"Could not find {term}. Scan again.", "danger")
            self._resolve_next_submitted_term()
        self._tasks.run(resolve, complete, failed)

    def _add_result_tuple_to_cart(self, result, clear_search=True):
        if self.session.pending_checkout:
            return
        product_id, product_name, price, batch_id, batch_qty, _batch_expiry = result[:6]
        metadata = result[6] if len(result) > 6 else {}
        product = {
            "prod_id": product_id,
            "name": product_name,
            "price": float(price),
            "batch_id": batch_id,
            "stock": batch_qty,
            "base_stock": metadata.get("base_stock", batch_qty),
            "unit_code": metadata.get("unit_code", "base"),
            "unit_label": metadata.get("unit_label", "unit"),
            "unit_multiplier": metadata.get("unit_multiplier", 1),
            "units": metadata.get("units", []),
        }
        self.session.add_to_cart(product, qty=1)
        if clear_search:
            self.txt_search.clear()
            self.hide_search_table(clear_feedback=True)
        self.refresh_cart_display()
        self.txt_search.setFocus()

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
        if self.session.pending_checkout:
            self.refresh_cart_display()
            return
        if item.column() != 3:
            return
        try:
            self.session.update_cart_qty(item.row(), int(item.text()))
            self.refresh_cart_display()
        except ValueError:
            self.toast.show_message("Enter a whole number for quantity.", ToastType.WARNING)
            self.refresh_cart_display()

    def on_cart_qty_delta(self, row: int, delta: int):
        if self.session.pending_checkout:
            return
        if 0 <= row < len(self.session.active_cart):
            current = self.session.active_cart[row]["qty"]
            self.session.update_cart_qty(row, current + delta)
            self.refresh_cart_display()
            if 0 <= row < self.cart_table.rowCount():
                self.cart_table.selectRow(row)

    def on_cust_text_changed(self, text: str):
        self.cust_search_timer.stop()
        self._tasks.invalidate("customer-search")
        self._customer_search_term = None
        self.selected_customer_cnic = None
        self.is_customer_verified = False
        self.cust_search_data = []
        self.cust_table.hide()
        self.lbl_cust_status.setText("Choose a customer from the results" if text.strip() else "Walk-in customer")
        set_tone(self.lbl_cust_status, "muted")
        value = text.strip()
        if not value:
            self.cust_table.hide()
            self.cust_search_data = []
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText("Walk-in customer")
            set_tone(self.lbl_cust_status, "muted")
            return
        self.cust_search_timer.start(120)

    def perform_customer_search(self):
        value = self.txt_customer.text().strip()
        if not value:
            self.cust_table.hide()
            return

        self._tasks.run_latest(
            "customer-search", lambda: _POS_CONTROLLER.search_customers(value),
            lambda customers: self._apply_customer_search(value, customers),
            lambda _details: self.lbl_cust_status.setText("Could not search customers. Try again."),
        )

    def _apply_customer_search(self, value, customers):
        if self.txt_customer.text().strip() != value or self.session.pending_checkout:
            return
        self._customer_search_term = value
        if not customers:
            self.cust_table.hide()
            self.cust_search_data = []
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText(
                "Customer not found. Use Add Credit Customer to create an account."
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
            self.selected_customer_cnic = cnic
            self.is_customer_verified = True
            self.txt_customer.blockSignals(True)
            self.txt_customer.setText(f"{first_name} {last_name} ({cnic})")
            self.txt_customer.blockSignals(False)
            self.cust_table.hide()
            self.lbl_cust_status.setText(
                f"{first_name} {last_name}".strip() + " • Checking balance…"
            )
            set_tone(self.lbl_cust_status, "accent", "bold")
            def loaded(debt):
                if self.selected_customer_cnic == cnic:
                    self.lbl_cust_status.setText(f"{first_name} {last_name}".strip() + f" • Due: Rs. {float(debt):,.2f}")
            self._tasks.run_latest("customer-balance", lambda: _POS_CONTROLLER.customer_total_debt(cnic), loaded,
                                   lambda _details: self.lbl_cust_status.setText("Customer selected. Balance unavailable."))

    def on_customer_lookup(self):
        self.cust_search_timer.stop()
        if self.is_customer_verified and self.selected_customer_cnic:
            return
        value = self.txt_customer.text().strip()
        if not value:
            self.selected_customer_cnic = None
            self.is_customer_verified = False
            self.lbl_cust_status.setText("Walk-in customer")
            set_tone(self.lbl_cust_status, "muted")
            return

        if (self._customer_search_term == value and self.cust_table.isVisible()
                and self.cust_table.rowCount() > 0):
            row = max(0, self.cust_table.currentRow())
            self.on_cust_table_double_clicked(self.cust_table.model().index(row, 0))
            return

        self.perform_customer_search()

    def eventFilter(self, watched, event):
        if watched is self.cust_table and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.on_cust_table_double_clicked(self.cust_table.model().index(self.cust_table.currentRow(), 0))
                return True
            if event.key() == Qt.Key_Escape:
                self.cust_table.hide()
                self.txt_customer.setFocus()
                return True
        return super().eventFilter(watched, event)

    def _quick_add_customer(self):
        from ui.screens.customer_screen import AddCustomerDialog
        dialog = AddCustomerDialog(self, initial_name=self.txt_customer.text().strip())
        if dialog.exec() != QDialog.Accepted:
            return
        customer_id = getattr(dialog, "created_customer_id", None)
        if not customer_id:
            return
        name = getattr(dialog, "created_customer_name", "Customer")
        self.txt_customer.blockSignals(True)
        self.txt_customer.setText(name)
        self.txt_customer.blockSignals(False)
        self.selected_customer_cnic = customer_id
        self.is_customer_verified = True
        self.cust_table.hide()
        self.lbl_cust_status.setText(name + " • New credit customer")

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
            for column in (0, 1, 2, 4, 5):
                cell = self.cart_table.item(row, column)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            units = item.get("units") or [{"code": item.get("unit_code", "base"),
                "label": item.get("unit_label", "unit"), "multiplier": item.get("unit_multiplier", 1),
                "price": item["price"]}]
            combo = QComboBox()
            combo.setAccessibleName(f"Selling unit for {item['name']}")
            for unit in units:
                combo.addItem(str(unit["label"]), unit)
            selected = next((i for i, unit in enumerate(units) if unit["code"] == item.get("unit_code", "base")), 0)
            combo.setCurrentIndex(selected)
            combo.setEnabled(len(units) > 1 and not self.session.pending_checkout)
            combo.currentIndexChanged.connect(lambda _index, row=row, combo=combo: self._change_cart_unit(row, combo.currentData()))
            self.cart_table.setCellWidget(row, 6, combo)

        self.cart_table.blockSignals(False)

        has_items = bool(self.session.active_cart)
        self.lbl_cart_empty.setVisible(not has_items)
        self.cart_table.setVisible(has_items)

        subtotal = self.session.get_cart_subtotal()
        self.session.discount_amount = self.spn_discount.value()
        net_total = self.session.get_cart_total()

        tax_rate = self._tax_rate
        net_dec = max(Decimal("0"), Decimal(str(net_total))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_dec = (net_dec * Decimal(str(tax_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_amount = float(tax_dec)
        total_with_tax = float(net_dec + tax_dec)
        self._displayed_total = total_with_tax

        cash_value = total_with_tax if self.chk_exact_cash.isChecked() else self.spn_cash_received.value()
        change_due = max(0.0, cash_value - total_with_tax) if cash_value > 0 else 0.0

        self.lbl_subtotal.setText(f"Subtotal: Rs. {subtotal:,.2f}")
        self.lbl_tax.setText(f"Tax ({tax_rate * 100:.2f}%): Rs. {tax_amount:,.2f}" if self._tax_ready else "Tax: checking settings…")
        self.lbl_total.setText(f"Total: Rs. {total_with_tax:,.2f}")
        shortfall = max(0.0, total_with_tax - cash_value)
        self.lbl_change.setText(f"Short: Rs. {shortfall:,.2f}" if shortfall > 0 else f"Change: Rs. {change_due:,.2f}")
        set_tone(self.lbl_change, "danger" if shortfall > 0 else "success", "bold")

    def _change_cart_unit(self, row, unit):
        if self.session.pending_checkout or not (0 <= row < len(self.session.active_cart)):
            return
        item = self.session.active_cart[row]
        item.update(unit_code=unit["code"], unit_label=unit["label"],
                    unit_multiplier=int(unit["multiplier"]), price=float(unit["price"]))
        item["subtotal"] = item["qty"] * item["price"]
        item["stock"] = int(item.get("base_stock", 0)) // item["unit_multiplier"]
        self.refresh_cart_display()

    def remove_cart_row(self, row: int):
        if self.session.pending_checkout:
            return
        self.session.remove_from_cart(row)
        self.refresh_cart_display()
        self.toast.show_message("Item removed", ToastType.INFO)

    def _reset_cart_state(self):
        self._sale_generation += 1
        self._submitted_terms.clear()
        self.session.clear_cart()
        self.spn_discount.setValue(0.0)
        self.spn_cash_received.setValue(0.0)
        self.chk_exact_cash.setChecked(True)
        self.cmb_pay_method.setCurrentIndex(0)
        self.txt_customer.clear()
        self.selected_customer_cnic = None
        self.is_customer_verified = False
        self.lbl_cust_status.setText("Walk-in customer")
        set_tone(self.lbl_cust_status, "muted")
        self.refresh_cart_display()

    def on_clear_cart_requested(self):
        if self.session.pending_checkout or self._checkout_in_progress:
            return
        if not self.session.active_cart:
            self.toast.show_message("There are no items to clear.", ToastType.INFO)
            return
        item_count = len(self.session.active_cart)
        self._cart_undo_cache = self._draft_snapshot()
        self._reset_cart_state()
        self.toast.show_message(
            f"Sale cleared ({item_count} item{'s' if item_count != 1 else ''} removed)",
            ToastType.INFO,
            duration_ms=4000,
            undo_callback=self._restore_cart_from_undo,
        )

    def on_clear_cart(self):
        if self.session.pending_checkout:
            return
        self._reset_cart_state()
        self.txt_search.setFocus()

    def _restore_cart_from_undo(self):
        if not self._cart_undo_cache:
            return
        if self.session.pending_checkout:
            return
        self._restore_draft(self._cart_undo_cache)
        self._cart_undo_cache = []
        self.refresh_cart_display()
        self.toast.show_message("Sale restored", ToastType.SUCCESS)

    def _draft_snapshot(self):
        return {
            "cart": copy.deepcopy(self.session.active_cart),
            "customer_id": self.selected_customer_cnic or "WALKIN",
            "customer_name": self.txt_customer.text(),
            "customer_verified": self.is_customer_verified,
            "selected_customer": {"id": self.selected_customer_cnic, "name": self.txt_customer.text()},
            "discount": self.spn_discount.value(),
            "payment_method": self.cmb_pay_method.currentData() or "Cash",
            "cash_received": None if self.chk_exact_cash.isChecked() else self.spn_cash_received.value(),
            "held_sale_id": self.session.held_sale_id,
        }

    def _restore_draft(self, draft):
        self.session.active_cart = copy.deepcopy(draft.get("cart", []))
        self.session.held_sale_id = draft.get("held_sale_id")
        self.spn_discount.setValue(float(draft.get("discount", 0)))
        index = self.cmb_pay_method.findData(draft.get("payment_method", "Cash"))
        self.cmb_pay_method.setCurrentIndex(max(0, index))
        received = draft.get("cash_received")
        self.chk_exact_cash.setChecked(received is None)
        self.spn_cash_received.setValue(float(received or 0))
        customer_id = draft.get("customer_id", "WALKIN")
        self.txt_customer.blockSignals(True)
        self.txt_customer.setText(draft.get("customer_name", "") if customer_id != "WALKIN" else "")
        self.txt_customer.blockSignals(False)
        self.selected_customer_cnic = customer_id if customer_id != "WALKIN" else None
        self.is_customer_verified = bool(self.selected_customer_cnic)
        self.lbl_cust_status.setText(draft.get("customer_name") or (f"Customer {customer_id}" if self.selected_customer_cnic else "Walk-in customer"))
        self.cust_table.hide()
        self.refresh_cart_display()

    def _set_checkout_notice(self, text="", tone="warning"):
        self.lbl_checkout_state.setText(text)
        self.lbl_checkout_state.setVisible(bool(text))
        set_tone(self.lbl_checkout_state, tone, "semibold")

    def _set_checkout_locked(self, locked):
        for control in (self.txt_search, self.txt_customer, self.cart_table,
                        self.spn_discount, self.cmb_pay_method, self.chk_exact_cash,
                        self.btn_clear, self.btn_hold, self.btn_recall, self.btn_add_customer):
            control.setEnabled(not locked)
        self.spn_cash_received.setEnabled(not locked and self.cmb_pay_method.currentData() == "Cash"
                                          and not self.chk_exact_cash.isChecked())
        self.sc_f3.setEnabled(not locked)
        self.sc_f4.setEnabled(not locked)
        self.sc_f5.setEnabled(not locked)
        self.sc_f6.setEnabled(not locked)

    def _restore_pending_checkout(self):
        pending = self.session.pending_checkout
        if not pending or self._checkout_in_progress:
            return
        self._set_checkout_locked(True)
        if pending.get("recovery_error"):
            self.btn_checkout.setEnabled(False)
            self._set_checkout_notice("We could not read this bill. Ask the owner to check the last saved sale before making another bill.", "danger")
            return
        self._restore_draft(pending["draft"])
        self.btn_checkout.setText("Check This Bill")
        self._pending_retry_ready = False
        self._set_checkout_notice("We need to check whether this bill was saved. Choose Check This Bill before taking payment again.")

    def on_hold_sale(self):
        if self.session.pending_checkout or self._checkout_in_progress:
            return
        if not self.session.active_cart:
            self.toast.show_message(
                "Add at least one item before holding the sale.", ToastType.WARNING
            )
            return

        self._hold_current_draft()

    def _hold_current_draft(self, after=None):
        if self._product_submit_active or self._submitted_terms:
            self._set_checkout_notice("Wait for the scanned products to finish loading before holding this bill.")
            return
        employee_id = self._current_employee_id()
        if employee_id is None:
            self._set_checkout_notice("Sign in again before completing the sale.", "danger")
            return
        draft = self._draft_snapshot()
        self._checkout_in_progress = True
        self._set_checkout_locked(True)
        self.btn_checkout.setEnabled(False)
        def complete(payload):
            self._checkout_in_progress = False
            self._set_checkout_locked(False)
            self.btn_checkout.setEnabled(True)
            if self._current_employee_id() != employee_id:
                return
            ok, result = payload
            if ok:
                self.on_clear_cart()
                self.toast.show_message("Sale held for later.", ToastType.SUCCESS)
                if after:
                    after()
            else:
                self.toast.show_message(f"Could not hold sale: {result}", ToastType.ERROR)
        self._tasks.run(
            lambda: _POS_CONTROLLER.hold_sale(draft["customer_id"], employee_id, draft["cart"], draft=draft),
            complete, lambda _details: complete((False, "Try again. The current bill has been kept.")),
        )

    def on_recall_sale(self):
        if self.session.pending_checkout or self._checkout_in_progress:
            return
        if self._product_submit_active or self._submitted_terms:
            self._set_checkout_notice("Wait for the scanned products to finish loading before resuming another bill.")
            return
        if self.session.active_cart:
            reply = QMessageBox.question(
                self, "Keep Current Sale", "Hold the current bill before resuming another sale?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._hold_current_draft(after=self._load_held_sales)
            return
        self._load_held_sales()

    def _load_held_sales(self):
        employee_id = self._current_employee_id()
        self._tasks.run(lambda: _POS_CONTROLLER.held_sales(employee_id), self._choose_held_sale,
                        lambda _details: self.toast.show_message("Could not load held sales. Try again.", ToastType.ERROR))

    def _choose_held_sale(self, held):
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

        self._checkout_in_progress = True
        self._set_checkout_locked(True)
        self.btn_checkout.setEnabled(False)
        employee_id = self._current_employee_id()
        def complete(payload):
            self._checkout_in_progress = False
            self._set_checkout_locked(False)
            self.btn_checkout.setEnabled(True)
            if self._current_employee_id() != employee_id:
                return
            ok, result = payload
            if ok and isinstance(result, dict) and "cart" in result:
                draft = copy.deepcopy(result.get("draft") or {})
                draft.update(cart=result["cart"], customer_id=result.get("customer_id", "WALKIN"), held_sale_id=hold_id)
                self._reset_cart_state()
                self._restore_draft(draft)
                self.toast.show_message("Held sale resumed. Check its quantities before completing.", ToastType.SUCCESS)
            else:
                self.toast.show_message(f"Could not resume sale: {result}", ToastType.ERROR)
            self.txt_search.setFocus()
        self._tasks.run(lambda: _POS_CONTROLLER.recall_sale(hold_id, employee_id), complete,
                        lambda _details: complete((False, "Try again.")))

    def on_checkout(self):
        if self._checkout_in_progress:
            return
        if self.session.pending_checkout:
            if self._pending_retry_ready:
                self._submit_pending_checkout()
            else:
                self._check_pending_checkout()
            return
        if self._product_submit_active or self._submitted_terms:
            self._set_checkout_notice("Wait for the scanned products to finish loading.")
            return
        if not self.session.active_cart:
            self.toast.show_message("Add at least one item before completing the sale.", ToastType.WARNING)
            return
        if not self._tax_ready:
            self._refresh_shift_state()
            self._set_checkout_notice("Checking tax settings. Try Complete Sale when the total is ready.")
            return
        employee_id = self._current_employee_id()
        if employee_id is None:
            self._set_checkout_notice("Sign in again before completing the sale.", "danger")
            return
        payment_method = self.cmb_pay_method.currentData() or "Cash"
        if payment_method == "Cash" and not self._cash_shift_open:
            if self.show_message_box:
                self._start_shift_from_pos()
            self._set_checkout_notice("Start a cash shift, then complete the sale.")
            return
        discount = self.spn_discount.value()
        subtotal = self.session.get_cart_subtotal()
        if discount > subtotal:
            self._set_checkout_notice("Discount cannot be greater than the sale subtotal.", "danger")
            return
        if payment_method == "Khatoo Credit" and not (self.selected_customer_cnic and self.is_customer_verified):
            self._set_checkout_notice("Choose a credit customer from the results or add a new customer.", "danger")
            self.txt_customer.setFocus()
            return
        cash_received = None
        if payment_method == "Cash" and not self.chk_exact_cash.isChecked():
            cash_received = self.spn_cash_received.value()
            amount_due = self._displayed_total
            if round(cash_received, 2) < round(amount_due, 2):
                self._set_checkout_notice(f"Cash is short by Rs. {amount_due-cash_received:,.2f}. Enter the cash received or use Exact Cash.", "danger")
                self.spn_cash_received.setFocus()
                return
        approval_token = None
        if subtotal > 0 and discount / subtotal * 100 > _POS_CONTROLLER.discount_threshold_pct:
            from ui.widgets.manager_auth_modal import ManagerAuthModal
            dialog = ManagerAuthModal(discount, subtotal, parent=self, employee_id=employee_id)
            if dialog.exec() != QDialog.Accepted or not dialog.approval_token:
                self._set_checkout_notice("Manager approval is required for this discount.", "danger")
                return
            approval_token = dialog.approval_token
        draft = self._draft_snapshot()
        try:
            request = _POS_CONTROLLER.checkout_request(
                customer_id=self.selected_customer_cnic or "WALKIN", employee_id=employee_id,
                cart=copy.deepcopy(self.session.active_cart), discount=discount,
                payment_method=payment_method, total=self.session.get_cart_total(),
                cash_received=cash_received, held_sale_id=self.session.held_sale_id,
                manager_approval_token=approval_token,
                expected_total=self._displayed_total,
            )
            self.session.save_pending_checkout(request, draft)
        except Exception:
            self._set_checkout_notice("Could not save this bill safely. No checkout was submitted. Check available disk space and try again.", "danger")
            return
        self._submit_pending_checkout()

    def _submit_pending_checkout(self):
        pending = self.session.pending_checkout
        if not pending or pending.get("recovery_error"):
            return
        # The saved request is the only source for submission/retry. Edits to
        # widgets or a new login can never change the work already submitted.
        try:
            request = _POS_CONTROLLER.checkout_request(**copy.deepcopy(pending["request"]))
        except (TypeError, ValueError):
            self._set_checkout_notice("The saved bill could not be loaded. Ask the owner to check its sale status before continuing.", "danger")
            return
        self._checkout_in_progress = True
        self._pending_retry_ready = False
        self._set_checkout_locked(True)
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setText("Completing Sale…")
        self._set_checkout_notice("Saving this sale. Wait for its result before taking another payment.")
        self._tasks.run(
            lambda: _POS_CONTROLLER.process_checkout(request),
            lambda result: self._checkout_finished(request, result),
            lambda _details: self._checkout_unknown(request),
        )

    def _pending_is_current(self, request):
        current = (self.session.pending_checkout or {}).get("request", {})
        return (self._current_employee_id() == int(request.employee_id)
                and current.get("checkout_token") == request.checkout_token)

    def _checkout_finished(self, request, result):
        self._checkout_in_progress = False
        if not self._pending_is_current(request):
            return
        self.btn_checkout.setEnabled(True)
        if result.success:
            try:
                self.session.clear_pending_checkout(request.employee_id, request.checkout_token)
            except (OSError, ValueError):
                self._checkout_unknown(request)
                self._set_checkout_notice("The bill is saved, but the last step did not finish. Choose Check This Bill before making another bill.", "danger")
                return
            self._last_sale_id = result.purchase_id
            total = float(getattr(result, "total", 0) or request.total * (1 + self._tax_rate))
            tender = getattr(result, "payment_method", None) or request.payment_method
            change = float(getattr(result, "change_due", 0) or 0)
            self.lbl_last_sale.setText(f"Sale #{result.purchase_id} saved • Rs. {total:,.2f}\n{tender}" +
                                       (f" • Change: Rs. {change:,.2f}" if tender == "Cash" else ""))
            self.last_sale_frame.show()
            self._set_checkout_locked(False)
            self.on_clear_cart()
            self.btn_checkout.setText("Complete Sale")
            self._set_checkout_notice("Sale saved. Use Reprint Last Receipt if the printer needs another copy.", "success")
            self._load_last_receipt_status(result.purchase_id)
            if getattr(result,'receipt_status','SAVED')=='PRINT_PENDING':
                self._set_checkout_notice(f'Sale #{result.purchase_id} saved. Receipt not printed: check this printer and use Reprint Last Receipt.','warning')
            self._refresh_shift_state()
        elif getattr(result, "outcome", "unknown") in {"rejected", "failed", "cancelled"}:
            try:
                self.session.clear_pending_checkout(request.employee_id, request.checkout_token)
            except (OSError, ValueError):
                self._checkout_unknown(request)
                return
            self._set_checkout_locked(False)
            self.btn_checkout.setText("Complete Sale")
            self._set_checkout_notice(f"Sale was not saved: {result.message}", "danger")
        else:
            self._checkout_unknown(request)
        self.txt_search.setFocus()

    def _checkout_unknown(self, request):
        self._checkout_in_progress = False
        if not self._pending_is_current(request):
            return
        self._pending_retry_ready = False
        self._set_checkout_locked(True)
        self.btn_checkout.setEnabled(True)
        self.btn_checkout.setText("Check This Bill")
        self._set_checkout_notice("We could not confirm whether the bill was saved. Choose Check This Bill. Do not take payment again yet.", "danger")

    def _check_pending_checkout(self):
        pending = self.session.pending_checkout
        if not pending or pending.get("recovery_error"):
            return
        request = SimpleNamespace(**copy.deepcopy(pending["request"]))
        self._checkout_in_progress = True
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setText("Checking Sale…")
        def complete(result):
            self._checkout_in_progress = False
            if not self._pending_is_current(request):
                return
            if result is not None:
                self._checkout_finished(request, result)
            else:
                self._pending_retry_ready = True
                self.btn_checkout.setEnabled(True)
                self.btn_checkout.setText("Try This Bill Again")
                self._set_checkout_notice("This bill has not been saved. Choose Try This Bill Again to finish it.")
        self._tasks.run(lambda: _POS_CONTROLLER.lookup_checkout_result(request.checkout_token, request.employee_id),
                        complete, lambda _details: self._checkout_unknown(request))

    def _reprint_last_sale(self):
        if not self._last_sale_id:
            return
        purchase_id = self._last_sale_id
        self.btn_reprint.setEnabled(False)
        self.btn_reprint.setText("Printing…")
        def complete(payload):
            self.btn_reprint.setEnabled(True)
            self.btn_reprint.setText("Reprint Last Receipt")
            ok, message = payload
            self._set_checkout_notice(f"Sale #{purchase_id}: {message}", "success" if ok else "warning")
        self._tasks.run(lambda: _POS_CONTROLLER.reprint_receipt(purchase_id), complete,
                        lambda _details: complete((False, "Receipt could not be printed. The sale is already saved; retry printing.")))

    def _load_last_receipt_status(self, purchase_id):
        def complete(saved):
            if self._last_sale_id != purchase_id:
                return
            if saved.get("print_status") == "PRINT_PENDING":
                self._set_checkout_notice(f"Sale #{purchase_id} saved. Receipt not printed: check the printer and use Reprint Last Receipt.")
            elif saved.get("print_status") == "SENT_TO_PRINTER":
                self._set_checkout_notice(f"Sale #{purchase_id} saved. Receipt sent to the printer.", "success")
        self._tasks.run(lambda: _POS_CONTROLLER.receipt_for_sale(purchase_id), complete,
                        lambda _details: self._set_checkout_notice(f"Sale #{purchase_id} saved. Receipt status unavailable; use Reprint Last Receipt if needed."))
