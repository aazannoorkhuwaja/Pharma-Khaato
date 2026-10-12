"""
Pharma-Khaato Native PySide6 Executive Reporting Analytics Screen
Features Sales KPI cards, daily sales summaries, low-stock reorder lists, and expiry alert reports.
"""

from datetime import date
import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFileDialog,
    QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, QDate

from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import Toast, ToastType, show_toast
from ui.widgets.table_polish import polish_table

from controllers.reports_controller import ReportsController

_REPORTS_CONTROLLER = ReportsController()

class ReportsScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Reports",
            "Review sales, low stock, expiring batches, and important system activity."
        )
        self.dt_picker = QDateEdit()
        self.dt_picker.setDate(QDate.currentDate())
        self.dt_picker.setCalendarPopup(True)
        self.dt_picker.dateChanged.connect(self.refresh_all_reports)
        header_card.add_widget(self.dt_picker)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_csv)
        header_card.add_widget(self.btn_export)
        layout.addWidget(header_card)

        # Executive metrics reflow from 4 columns to 2 on smaller workspaces.
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setHorizontalSpacing(12)
        self.kpi_grid.setVerticalSpacing(12)

        self.card_rev = self.create_kpi_card("Sales Total", "Rs. 0.00", ThemeTokens.SUCCESS)
        self.card_tx = self.create_kpi_card("Number of Sales", "0 Sales", ThemeTokens.ACCENT)
        self.card_cash = self.create_kpi_card("Cash", "Rs. 0.00", ThemeTokens.INFO)
        self.card_credit = self.create_kpi_card("Customer Credit", "Rs. 0.00", ThemeTokens.WARNING)
        self._kpi_cards = [self.card_rev, self.card_tx, self.card_cash, self.card_credit]
        self._kpi_columns = 0
        self._reflow_kpis(4)

        layout.addLayout(self.kpi_grid)

        # Tabbed Analytical Reports
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        # Tab 1: Low Stock Reorder Report
        tab_reorder = QWidget()
        lay_r = QVBoxLayout(tab_reorder)
        self.tbl_reorder = QTableWidget(0, 6)
        self.tbl_reorder.setHorizontalHeaderLabels(["ID", "Product", "Category", "In Stock", "Alert Level", "Price"])
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_reorder.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        polish_table(self.tbl_reorder)
        self.tbl_reorder.verticalHeader().setVisible(False)
        self.tbl_reorder.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_r.addWidget(self.tbl_reorder)
        self.tabs.addTab(tab_reorder, "Low Stock")

        # Tab 2: Expiry Alerts Report
        tab_expiry = QWidget()
        lay_e = QVBoxLayout(tab_expiry)
        self.tbl_expiry = QTableWidget(0, 6)
        self.tbl_expiry.setHorizontalHeaderLabels(["Product", "Batch", "Qty", "Expiry", "Days Left", "Category"])
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_expiry.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        polish_table(self.tbl_expiry)
        self.tbl_expiry.verticalHeader().setVisible(False)
        self.tbl_expiry.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_e.addWidget(self.tbl_expiry)
        self.tabs.addTab(tab_expiry, "Expiring Soon")

        # Tab 3: System Audit Trail
        tab_audit = QWidget()
        lay_a = QVBoxLayout(tab_audit)
        self.tbl_audit = QTableWidget(0, 4)
        self.tbl_audit.setHorizontalHeaderLabels(["ID", "Time", "User", "Activity"])
        self.tbl_audit.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        polish_table(self.tbl_audit)
        self.tbl_audit.verticalHeader().setVisible(False)
        self.tbl_audit.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_a.addWidget(self.tbl_audit)
        self.tabs.addTab(tab_audit, "Activity Log")


        layout.addWidget(self.tabs, 1)

        self.refresh_all_reports()

    def resizeEvent(self, event):
        if hasattr(self, "_kpi_cards"):
            columns = 4 if event.size().width() >= 1080 else 2
            self._reflow_kpis(columns)
        super().resizeEvent(event)

    def _reflow_kpis(self, columns: int):
        if columns == getattr(self, "_kpi_columns", 0):
            return
        self._kpi_columns = columns
        for card in self._kpi_cards:
            self.kpi_grid.removeWidget(card)
        for index, card in enumerate(self._kpi_cards):
            row, col = divmod(index, columns)
            self.kpi_grid.addWidget(card, row, col)
        for col in range(columns):
            self.kpi_grid.setColumnStretch(col, 1)

    def on_screen_show(self):
        """Auto-refreshes executive reports whenever screen is navigated to."""
        self.refresh_all_reports()

    def create_kpi_card(self, title: str, val: str, color: str) -> Card:
        card = Card()
        lay = card.layout()
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f" font-weight: 600; color: {ThemeTokens.TEXT_MUTED};")
        lbl_v = QLabel(val)
        lbl_v.setObjectName("val_label")
        lbl_v.setStyleSheet(f" font-weight: 800; color: {color};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        card.val_label = lbl_v
        return card

    def refresh_all_reports(self):
        sel_dt = self.dt_picker.date().toString("yyyy-MM-dd")

        # 1. Daily Sales Metrics
        sales_rep = _REPORTS_CONTROLLER.daily_sales(sel_dt)
        if sales_rep:
            self.card_rev.val_label.setText(f"Rs. {sales_rep['total_sales']:.2f}")
            self.card_tx.val_label.setText(f"{sales_rep['total_transactions']} Sales")
            self.card_cash.val_label.setText(f"Rs. {sales_rep['cash_sales']:.2f}")
            self.card_credit.val_label.setText(f"Rs. {sales_rep['credit_sales']:.2f}")
        else:
            self.card_rev.val_label.setText("Rs. 0.00")
            self.card_tx.val_label.setText("0 Sales")
            self.card_cash.val_label.setText("Rs. 0.00")
            self.card_credit.val_label.setText("Rs. 0.00")

        # 2. Reorder Stock
        reorder = _REPORTS_CONTROLLER.reorder_stock()
        self.tbl_reorder.setRowCount(len(reorder))
        for r, item in enumerate(reorder):
            self.tbl_reorder.setItem(r, 0, QTableWidgetItem(f"#{item['product_id']}"))
            self.tbl_reorder.setItem(r, 1, QTableWidgetItem(str(item['product_name'])))
            self.tbl_reorder.setItem(r, 2, QTableWidgetItem(str(item['category'])))
            self.tbl_reorder.setItem(r, 3, QTableWidgetItem(str(item['stock_quantity'])))
            self.tbl_reorder.setItem(r, 4, QTableWidgetItem(str(item['reorder_level'])))
            self.tbl_reorder.setItem(r, 5, QTableWidgetItem(f"Rs. {item['unit_price']:.2f}"))

        # 3. Expiry Risk
        expiries = _REPORTS_CONTROLLER.expiry_alert(60)
        self.tbl_expiry.setRowCount(len(expiries))
        for r, item in enumerate(expiries):
            self.tbl_expiry.setItem(r, 0, QTableWidgetItem(str(item['product_name'])))
            self.tbl_expiry.setItem(r, 1, QTableWidgetItem(f"#{item['batch_id']}"))
            self.tbl_expiry.setItem(r, 2, QTableWidgetItem(str(item['quantity'])))
            self.tbl_expiry.setItem(r, 3, QTableWidgetItem(str(item['expiry_date'])))
            self.tbl_expiry.setItem(r, 4, QTableWidgetItem(f"{item['days_left']} days"))
            self.tbl_expiry.setItem(r, 5, QTableWidgetItem(str(item['category'])))

        # 4. Audit Log
        audits = _REPORTS_CONTROLLER.audit_log(50)
        self.tbl_audit.setRowCount(len(audits))
        for r, item in enumerate(audits):
            self.tbl_audit.setItem(r, 0, QTableWidgetItem(f"#{item['id']}"))
            self.tbl_audit.setItem(r, 1, QTableWidgetItem(str(item['timestamp'])))
            self.tbl_audit.setItem(r, 2, QTableWidgetItem(str(item['username'])))
            self.tbl_audit.setItem(r, 3, QTableWidgetItem(f"[{item['event_type']}] {item['description']}"))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"PharmaKhaato_Report_{date.today()}.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["=== REORDER STOCK REPORT ==="])
                writer.writerow(["Product ID", "Product Name", "Category", "Stock", "Reorder Level", "Price"])
                for r in range(self.tbl_reorder.rowCount()):
                    row_data = [self.tbl_reorder.item(r, c).text() for c in range(self.tbl_reorder.columnCount())]
                    writer.writerow(row_data)

                writer.writerow([])
                writer.writerow(["=== EXPIRY RISK REPORT ==="])
                writer.writerow(["Product", "Batch", "Qty", "Expiry", "Days Left", "Category"])
                for r in range(self.tbl_expiry.rowCount()):
                    row_data = [self.tbl_expiry.item(r, c).text() for c in range(self.tbl_expiry.columnCount())]
                    writer.writerow(row_data)

            show_toast(self, f"Report saved to:\n{path}", ToastType.SUCCESS)
        except Exception as e:
            QMessageBox.critical(self, "Could Not Export", f"Could not save the CSV file: {e}")
