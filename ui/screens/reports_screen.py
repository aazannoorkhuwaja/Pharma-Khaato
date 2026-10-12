"""
Pharma-Khaato Native PySide6 Reporting Screen
Sales, low-stock, expiry, and activity reports for day-to-day pharmacy use.
"""

from datetime import date
import csv

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFileDialog,
    QMessageBox, QTabWidget
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
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Reports",
            "Review sales, low stock, expiring products, and important activity."
        )
        self.dt_picker = QDateEdit()
        self.dt_picker.setDate(QDate.currentDate())
        self.dt_picker.setCalendarPopup(True)
        self.dt_picker.setAccessibleName("Report date")
        self.dt_picker.dateChanged.connect(self.refresh_all_reports)
        header_card.add_widget(self.dt_picker)

        self.btn_export = QPushButton("Export Report")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_csv)
        header_card.add_widget(self.btn_export)
        layout.addWidget(header_card)

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

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        tab_reorder = QWidget()
        lay_r = QVBoxLayout(tab_reorder)
        self.tbl_reorder = QTableWidget(0, 6)
        self.tbl_reorder.setHorizontalHeaderLabels(
            ["ID", "Product", "Category", "In Stock", "Alert Level", "Price"]
        )
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

        tab_expiry = QWidget()
        lay_e = QVBoxLayout(tab_expiry)
        self.tbl_expiry = QTableWidget(0, 6)
        self.tbl_expiry.setHorizontalHeaderLabels(
            ["Product", "Batch", "Qty", "Expiry", "Days Left", "Category"]
        )
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
        self.refresh_all_reports()

    def create_kpi_card(self, title: str, val: str, color: str) -> Card:
        card = Card()
        lay = card.layout()
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_MUTED};")
        lbl_v = QLabel(val)
        lbl_v.setObjectName("val_label")
        lbl_v.setStyleSheet(f"font-weight: 800; color: {color};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        card.val_label = lbl_v
        return card

    def refresh_all_reports(self):
        selected_date = self.dt_picker.date().toString("yyyy-MM-dd")

        sales = _REPORTS_CONTROLLER.daily_sales(selected_date)
        if sales:
            self.card_rev.val_label.setText(f"Rs. {sales['total_sales']:.2f}")
            self.card_tx.val_label.setText(f"{sales['total_transactions']} Sales")
            self.card_cash.val_label.setText(f"Rs. {sales['cash_sales']:.2f}")
            self.card_credit.val_label.setText(f"Rs. {sales['credit_sales']:.2f}")
        else:
            self.card_rev.val_label.setText("Rs. 0.00")
            self.card_tx.val_label.setText("0 Sales")
            self.card_cash.val_label.setText("Rs. 0.00")
            self.card_credit.val_label.setText("Rs. 0.00")

        reorder = _REPORTS_CONTROLLER.reorder_stock()
        self.tbl_reorder.setRowCount(len(reorder))
        for row, item in enumerate(reorder):
            self.tbl_reorder.setItem(row, 0, QTableWidgetItem(str(item['product_id'])))
            self.tbl_reorder.setItem(row, 1, QTableWidgetItem(str(item['product_name'])))
            self.tbl_reorder.setItem(row, 2, QTableWidgetItem(str(item['category'])))
            self.tbl_reorder.setItem(row, 3, QTableWidgetItem(str(item['stock_quantity'])))
            self.tbl_reorder.setItem(row, 4, QTableWidgetItem(str(item['reorder_level'])))
            self.tbl_reorder.setItem(row, 5, QTableWidgetItem(f"Rs. {item['unit_price']:.2f}"))

        expiries = _REPORTS_CONTROLLER.expiry_alert(60)
        self.tbl_expiry.setRowCount(len(expiries))
        for row, item in enumerate(expiries):
            self.tbl_expiry.setItem(row, 0, QTableWidgetItem(str(item['product_name'])))
            self.tbl_expiry.setItem(row, 1, QTableWidgetItem(str(item['batch_id'])))
            self.tbl_expiry.setItem(row, 2, QTableWidgetItem(str(item['quantity'])))
            self.tbl_expiry.setItem(row, 3, QTableWidgetItem(str(item['expiry_date'])))
            self.tbl_expiry.setItem(row, 4, QTableWidgetItem(f"{item['days_left']} days"))
            self.tbl_expiry.setItem(row, 5, QTableWidgetItem(str(item['category'])))

        audits = _REPORTS_CONTROLLER.audit_log(50)
        self.tbl_audit.setRowCount(len(audits))
        for row, item in enumerate(audits):
            self.tbl_audit.setItem(row, 0, QTableWidgetItem(str(item['id'])))
            self.tbl_audit.setItem(row, 1, QTableWidgetItem(str(item['timestamp'])))
            self.tbl_audit.setItem(row, 2, QTableWidgetItem(str(item['username'])))
            self.tbl_audit.setItem(
                row, 3,
                QTableWidgetItem(f"[{item['event_type']}] {item['description']}")
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
            values.append(item.text() if item is not None else "")
        return values

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            f"PharmaKhaato_Report_{date.today()}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle)

                writer.writerow(["LOW STOCK"])
                writer.writerow(self._visible_headers(self.tbl_reorder))
                for row in range(self.tbl_reorder.rowCount()):
                    writer.writerow(self._visible_row(self.tbl_reorder, row))

                writer.writerow([])
                writer.writerow(["EXPIRING SOON"])
                writer.writerow(self._visible_headers(self.tbl_expiry))
                for row in range(self.tbl_expiry.rowCount()):
                    writer.writerow(self._visible_row(self.tbl_expiry, row))

            show_toast(self, f"Report saved to:\n{path}", ToastType.SUCCESS)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Could Not Export",
                f"Could not save the report file: {exc}",
            )
