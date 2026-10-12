"""Fast day-to-day sales, stock, expiry, and activity reports."""

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
from controllers.reports_controller import ReportsController

_REPORTS_CONTROLLER = ReportsController()


class ReportsScreen(QWidget):
    """Reports screen that loads only the data the user is looking at."""

    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._loaded_tabs = set()

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
        self.dt_picker.dateChanged.connect(self._on_date_changed)
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

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.currentChanged.connect(self._load_current_tab)

        tab_reorder = QWidget()
        lay_r = QVBoxLayout(tab_reorder)
        self.tbl_reorder = QTableWidget(0, 5)
        self.tbl_reorder.setHorizontalHeaderLabels(
            ["Product", "Category", "In Stock", "Alert Level", "Price"]
        )
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            self.tbl_reorder.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        polish_table(self.tbl_reorder)
        self.tbl_reorder.verticalHeader().setVisible(False)
        self.tbl_reorder.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_r.addWidget(self.tbl_reorder)
        self.tabs.addTab(tab_reorder, "Low Stock")

        tab_expiry = QWidget()
        lay_e = QVBoxLayout(tab_expiry)
        self.tbl_expiry = QTableWidget(0, 5)
        self.tbl_expiry.setHorizontalHeaderLabels(
            ["Product", "Qty", "Expiry", "Days Left", "Category"]
        )
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            self.tbl_expiry.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        polish_table(self.tbl_expiry)
        self.tbl_expiry.verticalHeader().setVisible(False)
        self.tbl_expiry.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_e.addWidget(self.tbl_expiry)
        self.tabs.addTab(tab_expiry, "Expiring Soon")

        tab_audit = QWidget()
        lay_a = QVBoxLayout(tab_audit)
        self.tbl_audit = QTableWidget(0, 3)
        self.tbl_audit.setHorizontalHeaderLabels(["Time", "User", "Activity"])
        self.tbl_audit.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        polish_table(self.tbl_audit)
        self.tbl_audit.verticalHeader().setVisible(False)
        self.tbl_audit.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_a.addWidget(self.tbl_audit)
        self.tabs.addTab(tab_audit, "Activity Log")

        layout.addWidget(self.tabs, 1)
        self._refresh_financials()
        self._load_current_tab(0)

    def resizeEvent(self, event):
        if hasattr(self, "_kpi_cards"):
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
            row, col = divmod(index, columns)
            self.kpi_grid.addWidget(card, row, col)
        for col in range(columns):
            self.kpi_grid.setColumnStretch(col, 1)

    def create_kpi_card(self, title: str, value: str, color: str) -> Card:
        card = Card()
        lay = card.layout()
        label = QLabel(title)
        label.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_MUTED};")
        val = QLabel(value)
        val.setObjectName("val_label")
        val.setStyleSheet(f"font-weight: 800; color: {color};")
        lay.addWidget(label)
        lay.addWidget(val)
        card.val_label = val
        return card

    def _selected_date(self):
        return self.dt_picker.date().toString("yyyy-MM-dd")

    def _on_date_changed(self, *_):
        # Date changes affect financial KPIs only. Stock/expiry/audit are not
        # re-queried unnecessarily.
        self._refresh_financials()

    def _refresh_financials(self):
        selected_date = self._selected_date()
        sales = _REPORTS_CONTROLLER.daily_sales(selected_date) or {}
        collections = _REPORTS_CONTROLLER.credit_collections(selected_date) or {}
        self.card_total.val_label.setText(f"Rs. {float(sales.get('total_sales', 0)):.2f}")
        self.card_tx.val_label.setText(str(int(sales.get("total_transactions", 0))))
        self.card_cash.val_label.setText(f"Rs. {float(sales.get('cash_sales', 0)):.2f}")
        self.card_digital.val_label.setText(f"Rs. {float(sales.get('digital_sales', 0)):.2f}")
        self.card_credit.val_label.setText(f"Rs. {float(sales.get('credit_sales', 0)):.2f}")
        self.card_collections.val_label.setText(f"Rs. {float(collections.get('total', 0)):.2f}")

    def _load_current_tab(self, index):
        if index == 0:
            self._refresh_low_stock()
        elif index == 1:
            self._refresh_expiry()
        elif index == 2:
            self._refresh_audit()

    def _refresh_low_stock(self):
        rows = _REPORTS_CONTROLLER.reorder_stock()
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
        self._loaded_tabs.add(0)

    def _refresh_expiry(self):
        rows = _REPORTS_CONTROLLER.expiry_alert(60)
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
        self._loaded_tabs.add(1)

    def _refresh_audit(self):
        rows = _REPORTS_CONTROLLER.audit_log(75)
        self.tbl_audit.setUpdatesEnabled(False)
        try:
            self.tbl_audit.setRowCount(len(rows))
            for row, item in enumerate(rows):
                self.tbl_audit.setItem(row, 0, QTableWidgetItem(str(item["timestamp"])))
                self.tbl_audit.setItem(row, 1, QTableWidgetItem(str(item["username"])))
                self.tbl_audit.setItem(row, 2, QTableWidgetItem(f"[{item['event_type']}] {item['description']}"))
        finally:
            self.tbl_audit.setUpdatesEnabled(True)
        self._loaded_tabs.add(2)

    def refresh_all_reports(self):
        self._refresh_financials()
        self._load_current_tab(self.tabs.currentIndex())

    def on_screen_show(self):
        self.refresh_all_reports()

    @staticmethod
    def _headers(table):
        return [
            table.horizontalHeaderItem(col).text() if table.horizontalHeaderItem(col) else ""
            for col in range(table.columnCount()) if not table.isColumnHidden(col)
        ]

    @staticmethod
    def _row(table, row):
        values = []
        for col in range(table.columnCount()):
            if table.isColumnHidden(col):
                continue
            item = table.item(row, col)
            values.append(item.text() if item else "")
        return values

    def export_csv(self):
        # Ensure export is complete even if those tabs have not been opened.
        self._refresh_low_stock()
        self._refresh_expiry()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Stock Report",
            f"PharmaKhaato_Stock_{date.today()}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["LOW STOCK"])
                writer.writerow(self._headers(self.tbl_reorder))
                for row in range(self.tbl_reorder.rowCount()):
                    writer.writerow(self._row(self.tbl_reorder, row))
                writer.writerow([])
                writer.writerow(["EXPIRING SOON"])
                writer.writerow(self._headers(self.tbl_expiry))
                for row in range(self.tbl_expiry.rowCount()):
                    writer.writerow(self._row(self.tbl_expiry, row))
            show_toast(self, f"Report saved to:\n{path}", ToastType.SUCCESS)
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Export", f"Could not save the report file: {exc}")
