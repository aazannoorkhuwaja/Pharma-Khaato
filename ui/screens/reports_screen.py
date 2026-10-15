"""Responsive day-to-day sales, stock, expiry, and activity reports."""

from datetime import date
import csv

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFileDialog,
    QMessageBox, QTabWidget,
)
from PySide6.QtCore import QDate

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.inline_state import InlineState
from ui.app.async_tasks import AsyncTaskRunner
from controllers.reports_controller import ReportsController

_REPORTS_CONTROLLER = ReportsController()


class ReportsScreen(QWidget):
    """Keep report navigation responsive while database work runs in workers."""

    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._tasks = AsyncTaskRunner(self)
        self._loaded_tabs: set[int] = set()
        self._loading_tabs: set[int] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = ScreenHeader(
            "Reports",
            "Review sales, payment mix, collections, low stock, expiry, and activity."
        )
        self.dt_picker = QDateEdit()
        self.dt_picker.setDate(QDate.currentDate())
        self.dt_picker.setCalendarPopup(True)
        self.dt_picker.setAccessibleName("Report date")
        self.dt_picker.dateChanged.connect(self._refresh_financials)
        header.add_widget(self.dt_picker)

        self.btn_export = QPushButton("Export Stock Report")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_csv)
        header.add_widget(self.btn_export)
        layout.addWidget(header)

        self.kpi_grid = QGridLayout()
        self.kpi_grid.setHorizontalSpacing(12)
        self.kpi_grid.setVerticalSpacing(12)
        self.card_total = self.create_kpi_card("Sales Total", "Rs. 0.00", ThemeTokens.SUCCESS)
        self.card_tx = self.create_kpi_card("Number of Sales", "0", ThemeTokens.ACCENT)
        self.card_cash = self.create_kpi_card("Cash Sales", "Rs. 0.00", ThemeTokens.INFO)
        self.card_digital = self.create_kpi_card("Card & Wallets", "Rs. 0.00", ThemeTokens.ACCENT)
        self.card_credit = self.create_kpi_card("Customer Credit Sales", "Rs. 0.00", ThemeTokens.WARNING)
        self.card_collections = self.create_kpi_card("Credit Collected", "Rs. 0.00", ThemeTokens.SUCCESS)
        self._kpi_cards = [
            self.card_total, self.card_tx, self.card_cash,
            self.card_digital, self.card_credit, self.card_collections,
        ]
        self._kpi_columns = 0
        self._reflow_kpis(3)
        layout.addLayout(self.kpi_grid)
        self.financial_state = InlineState()
        layout.addWidget(self.financial_state)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        low_stock_tab = QWidget()
        low_layout = QVBoxLayout(low_stock_tab)
        self.state_reorder = InlineState()
        low_layout.addWidget(self.state_reorder)
        self.tbl_reorder = QTableWidget(0, 5)
        self.tbl_reorder.setHorizontalHeaderLabels(
            ["Product", "Category", "In Stock", "Alert Level", "Price"]
        )
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 5):
            self.tbl_reorder.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        polish_table(self.tbl_reorder)
        self.tbl_reorder.verticalHeader().setVisible(False)
        self.tbl_reorder.setEditTriggers(QTableWidget.NoEditTriggers)
        low_layout.addWidget(self.tbl_reorder)
        self.tabs.addTab(low_stock_tab, "Low Stock")

        expiry_tab = QWidget()
        expiry_layout = QVBoxLayout(expiry_tab)
        self.state_expiry = InlineState()
        expiry_layout.addWidget(self.state_expiry)
        self.tbl_expiry = QTableWidget(0, 5)
        self.tbl_expiry.setHorizontalHeaderLabels(
            ["Product", "Qty", "Expiry", "Days Left", "Category"]
        )
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 5):
            self.tbl_expiry.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        polish_table(self.tbl_expiry)
        self.tbl_expiry.verticalHeader().setVisible(False)
        self.tbl_expiry.setEditTriggers(QTableWidget.NoEditTriggers)
        expiry_layout.addWidget(self.tbl_expiry)
        self.tabs.addTab(expiry_tab, "Expiring Soon")

        audit_tab = QWidget()
        audit_layout = QVBoxLayout(audit_tab)
        self.state_audit = InlineState()
        audit_layout.addWidget(self.state_audit)
        self.tbl_audit = QTableWidget(0, 3)
        self.tbl_audit.setHorizontalHeaderLabels(["Time", "User", "Activity"])
        self.tbl_audit.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        polish_table(self.tbl_audit)
        self.tbl_audit.verticalHeader().setVisible(False)
        self.tbl_audit.setEditTriggers(QTableWidget.NoEditTriggers)
        audit_layout.addWidget(self.tbl_audit)
        self.tabs.addTab(audit_tab, "Activity Log")

        self.tabs.currentChanged.connect(self._load_current_tab)
        layout.addWidget(self.tabs, 1)

        # These methods only schedule work; the screen can paint immediately.
        self._refresh_financials()
        self._load_current_tab(self.tabs.currentIndex())

    def resizeEvent(self, event):
        width = event.size().width()
        columns = 3 if width >= 1000 else (2 if width >= 720 else 1)
        self._reflow_kpis(columns)
        super().resizeEvent(event)

    def _reflow_kpis(self, columns: int):
        if columns == self._kpi_columns:
            return
        self._kpi_columns = columns
        for card in self._kpi_cards:
            self.kpi_grid.removeWidget(card)
        for index, card in enumerate(self._kpi_cards):
            row, column = divmod(index, columns)
            self.kpi_grid.addWidget(card, row, column)
        for column in range(columns):
            self.kpi_grid.setColumnStretch(column, 1)

    def create_kpi_card(self, title: str, value: str, color: str) -> Card:
        card = Card()
        card_layout = card.layout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_MUTED};")
        value_label = QLabel(value)
        value_label.setObjectName("val_label")
        value_label.setStyleSheet(f"font-weight: 800; color: {color};")
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card.val_label = value_label
        return card

    def _selected_date(self):
        return self.dt_picker.date().toString("yyyy-MM-dd")

    def _set_financials_loading(self):
        for card in self._kpi_cards:
            card.val_label.setText("…")
        self.financial_state.show_loading("Loading sales and collection totals…")

    def _refresh_financials(self, *_):
        selected_date = self._selected_date()
        self._set_financials_loading()

        def load():
            return (
                _REPORTS_CONTROLLER.daily_sales(selected_date) or {},
                _REPORTS_CONTROLLER.credit_collections(selected_date) or {},
            )

        self._tasks.run_latest(
            "reports-financials",
            load,
            self._apply_financials,
            self._financials_failed,
        )

    def _apply_financials(self, payload):
        sales, collections = payload
        transactions = int(sales.get("total_transactions", 0))
        collected = float(collections.get("total", 0))
        self.card_total.val_label.setText(f"Rs. {float(sales.get('total_sales', 0)):.2f}")
        self.card_tx.val_label.setText(str(transactions))
        self.card_cash.val_label.setText(f"Rs. {float(sales.get('cash_sales', 0)):.2f}")
        self.card_digital.val_label.setText(f"Rs. {float(sales.get('digital_sales', 0)):.2f}")
        self.card_credit.val_label.setText(f"Rs. {float(sales.get('credit_sales', 0)):.2f}")
        self.card_collections.val_label.setText(f"Rs. {collected:.2f}")
        if transactions == 0 and collected == 0:
            self.financial_state.show_empty(
                f"No sales or customer-credit collections recorded for {self._selected_date()}."
            )
        else:
            self.financial_state.clear()

    def _financials_failed(self, _details):
        for card in self._kpi_cards:
            card.val_label.setText("—")
        self.financial_state.show_error(
            "Could not load the financial summary.", self._refresh_financials
        )
        self._task_failed("financial summary", _details)

    def _state_for_tab(self, index: int) -> InlineState:
        return (self.state_reorder, self.state_expiry, self.state_audit)[int(index)]

    def _retry_tab(self, index: int):
        self._loaded_tabs.discard(int(index))
        self._loading_tabs.discard(int(index))
        self._load_current_tab(int(index))

    def _load_current_tab(self, index):
        index = int(index)
        if index in self._loaded_tabs or index in self._loading_tabs:
            return
        self._loading_tabs.add(index)

        if index == 0:
            key = "reports-low-stock"
            fn = _REPORTS_CONTROLLER.reorder_stock
            apply = self._populate_low_stock
            loading_text = "Checking products that need reordering…"
            empty_text = "Stock levels are healthy — no products currently need reordering."
        elif index == 1:
            key = "reports-expiry"
            fn = lambda: _REPORTS_CONTROLLER.expiry_alert(60)
            apply = self._populate_expiry
            loading_text = "Checking stock that expires within 60 days…"
            empty_text = "No stocked batches expire within the next 60 days."
        elif index == 2:
            key = "reports-audit"
            fn = lambda: _REPORTS_CONTROLLER.audit_log(75)
            apply = self._populate_audit
            loading_text = "Loading recent staff activity…"
            empty_text = "No recent activity has been recorded yet."
        else:
            self._loading_tabs.discard(index)
            return

        state = self._state_for_tab(index)
        state.show_loading(loading_text)

        def completed(rows):
            self._loading_tabs.discard(index)
            self._loaded_tabs.add(index)
            rows = list(rows or [])
            apply(rows)
            if rows:
                state.clear()
            else:
                state.show_empty(empty_text)

        def failed(message):
            self._loading_tabs.discard(index)
            state.show_error(
                "Could not load this report. Check the database status and try again.",
                lambda: self._retry_tab(index),
            )
            self._task_failed("report table", message)

        self._tasks.run_latest(key, fn, completed, failed)

    def _populate_low_stock(self, rows):
        self.tbl_reorder.setUpdatesEnabled(False)
        try:
            self.tbl_reorder.setRowCount(len(rows))
            for row, item in enumerate(rows):
                self.tbl_reorder.setItem(row, 0, QTableWidgetItem(str(item["product_name"])))
                self.tbl_reorder.setItem(row, 1, QTableWidgetItem(str(item["category"])))
                self.tbl_reorder.setItem(row, 2, QTableWidgetItem(str(item["stock_quantity"])))
                self.tbl_reorder.setItem(row, 3, QTableWidgetItem(str(item["reorder_level"])))
                self.tbl_reorder.setItem(row, 4, QTableWidgetItem(f"Rs. {float(item['unit_price']):.2f}"))
        finally:
            self.tbl_reorder.setUpdatesEnabled(True)

    def _populate_expiry(self, rows):
        self.tbl_expiry.setUpdatesEnabled(False)
        try:
            self.tbl_expiry.setRowCount(len(rows))
            for row, item in enumerate(rows):
                self.tbl_expiry.setItem(row, 0, QTableWidgetItem(str(item["product_name"])))
                self.tbl_expiry.setItem(row, 1, QTableWidgetItem(str(item["quantity"])))
                self.tbl_expiry.setItem(row, 2, QTableWidgetItem(str(item["expiry_date"])))
                self.tbl_expiry.setItem(row, 3, QTableWidgetItem(f"{item['days_left']} days"))
                self.tbl_expiry.setItem(row, 4, QTableWidgetItem(str(item["category"])))
        finally:
            self.tbl_expiry.setUpdatesEnabled(True)

    def _populate_audit(self, rows):
        self.tbl_audit.setUpdatesEnabled(False)
        try:
            self.tbl_audit.setRowCount(len(rows))
            for row, item in enumerate(rows):
                self.tbl_audit.setItem(row, 0, QTableWidgetItem(str(item["timestamp"])))
                self.tbl_audit.setItem(row, 1, QTableWidgetItem(str(item["username"])))
                self.tbl_audit.setItem(row, 2, QTableWidgetItem(f"[{item['event_type']}] {item['description']}"))
        finally:
            self.tbl_audit.setUpdatesEnabled(True)

    # Backward-compatible method names retained for tests/callers. They now
    # invalidate and schedule worker-backed refreshes instead of blocking Qt.
    def _refresh_low_stock(self):
        self._loaded_tabs.discard(0)
        self._load_current_tab(0)

    def _refresh_expiry(self):
        self._loaded_tabs.discard(1)
        self._load_current_tab(1)

    def _refresh_audit(self):
        self._loaded_tabs.discard(2)
        self._load_current_tab(2)

    def refresh_all_reports(self):
        self._loaded_tabs.clear()
        self._refresh_financials()
        self._load_current_tab(self.tabs.currentIndex())

    def on_screen_show(self):
        self.refresh_all_reports()

    def _task_failed(self, context: str, _details: str):
        if self.show_message_box:
            show_toast(
                self,
                f"Could not load {context}. Try again.",
                ToastType.WARNING,
            )

    @staticmethod
    def _visible_headers(table):
        headers = []
        for column in range(table.columnCount()):
            if table.isColumnHidden(column):
                continue
            item = table.horizontalHeaderItem(column)
            headers.append(item.text() if item else "")
        return headers

    @staticmethod
    def _visible_row(table, row: int):
        values = []
        for column in range(table.columnCount()):
            if table.isColumnHidden(column):
                continue
            item = table.item(row, column)
            values.append(item.text() if item else "")
        return values

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Stock Report",
            f"PharmaKhaato_Stock_{date.today()}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        self.btn_export.setEnabled(False)
        self.btn_export.setText("Exporting…")

        def create_export():
            low_rows = _REPORTS_CONTROLLER.reorder_stock() or []
            expiry_rows = _REPORTS_CONTROLLER.expiry_alert(60) or []
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["LOW STOCK"])
                writer.writerow(["Product", "Category", "In Stock", "Alert Level", "Price"])
                for item in low_rows:
                    writer.writerow([
                        item["product_name"],
                        item["category"],
                        item["stock_quantity"],
                        item["reorder_level"],
                        f"Rs. {float(item['unit_price']):.2f}",
                    ])
                writer.writerow([])
                writer.writerow(["EXPIRING SOON"])
                writer.writerow(["Product", "Qty", "Expiry", "Days Left", "Category"])
                for item in expiry_rows:
                    writer.writerow([
                        item["product_name"],
                        item["quantity"],
                        item["expiry_date"],
                        item["days_left"],
                        item["category"],
                    ])
            return path

        def complete(saved_path):
            self.btn_export.setEnabled(True)
            self.btn_export.setText("Export Stock Report")
            show_toast(self, f"Report saved to:\n{saved_path}", ToastType.SUCCESS)

        def failed(_message):
            self.btn_export.setEnabled(True)
            self.btn_export.setText("Export Stock Report")
            QMessageBox.critical(self, "Could Not Export", "Could not save the report file. Try another location.")

        self._tasks.run_latest("reports-export", create_export, complete, failed)
