"""Reusable POS input, result, cart, and held-sale widgets."""

import json

from PySide6.QtWidgets import (
    QLineEdit, QTableView, QTableWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt

from ui.theme.tokens import ThemeTokens
from ui.widgets.responsive import configure_dialog
from ui.widgets.table_polish import polish_table


class SearchLineEdit(QLineEdit):
    """Search input with Down-arrow and Escape navigation helpers."""

    def __init__(self, parent=None, on_down_callback=None, on_escape_callback=None):
        super().__init__(parent)
        self.on_down_callback = on_down_callback
        self.on_escape_callback = on_escape_callback

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            if self.on_down_callback and self.on_down_callback():
                return
        elif event.key() == Qt.Key_Escape:
            if self.on_escape_callback:
                self.on_escape_callback()
                return
        super().keyPressEvent(event)


class SearchResultsTable(QTableView):
    """Virtualized product-result table with keyboard selection."""

    def __init__(self, parent=None, on_select_callback=None, on_cancel_callback=None):
        super().__init__(parent)
        self.on_select_callback = on_select_callback
        self.on_cancel_callback = on_cancel_callback
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setEditTriggers(QTableView.NoEditTriggers)
        self.setShowGrid(True)

    def currentRow(self):
        indexes = self.selectedIndexes()
        if indexes:
            return indexes[0].row()
        return 0 if self.model() and self.model().rowCount() > 0 else -1

    def rowCount(self):
        return self.model().rowCount() if self.model() else 0

    def selectRow(self, row):
        if self.model() and 0 <= row < self.model().rowCount():
            self.setCurrentIndex(self.model().index(row, 0))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            row = self.currentRow()
            if row >= 0 and self.on_select_callback:
                self.on_select_callback(row)
                return
        elif event.key() == Qt.Key_Escape:
            if self.on_cancel_callback:
                self.on_cancel_callback()
                return
        elif event.key() == Qt.Key_Up and self.currentRow() == 0:
            if self.on_cancel_callback:
                self.on_cancel_callback()
                return
        super().keyPressEvent(event)


class CartTableWidget(QTableWidget):
    """Cart table with Delete and +/- keyboard quantity controls."""

    def __init__(self, parent=None, on_delete_callback=None, on_qty_change_callback=None):
        super().__init__(0, 6, parent)
        self.on_delete_callback = on_delete_callback
        self.on_qty_change_callback = on_qty_change_callback

    def keyPressEvent(self, event):
        row = self.currentRow()
        if row >= 0:
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                if self.on_delete_callback:
                    self.on_delete_callback(row)
                    return
            elif event.key() in (Qt.Key_Plus, Qt.Key_Equal):
                if self.on_qty_change_callback:
                    self.on_qty_change_callback(row, 1)
                    return
            elif event.key() in (Qt.Key_Minus, Qt.Key_Hyphen):
                if self.on_qty_change_callback:
                    self.on_qty_change_callback(row, -1)
                    return
        super().keyPressEvent(event)


class RecallSaleDialog(QDialog):
    """Choose a held sale without exposing internal hold IDs."""

    def __init__(self, held_sales, parent=None):
        super().__init__(parent)
        self.selected_hold_id = None
        self.setWindowTitle("Held Sales")
        configure_dialog(self, 680, 440, minimum_width=500, minimum_height=340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Held Sales")
        title.setObjectName("h2")
        title.setStyleSheet(f"font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(title)

        subtitle = QLabel("Choose the sale you want to continue.")
        subtitle.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(subtitle)

        self.table = QTableWidget(len(held_sales), 4)
        self.table.setHorizontalHeaderLabels(["Held At", "Customer", "Items", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.table)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAccessibleName("Held sales")

        self.held_ids = []
        for row, item in enumerate(held_sales):
            hold_id, held_at, customer_id, _employee_id, cart_json, _note = item
            self.held_ids.append(hold_id)
            try:
                cart_data = json.loads(cart_json)
                item_count = sum(int(entry.get("qty", 1)) for entry in cart_data)
                total = sum(float(entry.get("subtotal", 0.0)) for entry in cart_data)
            except (TypeError, ValueError, json.JSONDecodeError):
                item_count = 0
                total = 0.0

            customer_text = "Walk-in customer" if str(customer_id) == "WALKIN" else str(customer_id)
            self.table.setItem(row, 0, QTableWidgetItem(str(held_at)))
            self.table.setItem(row, 1, QTableWidgetItem(customer_text))
            self.table.setItem(row, 2, QTableWidgetItem(str(item_count)))
            self.table.setItem(row, 3, QTableWidgetItem(f"Rs. {total:.2f}"))

        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.btn_recall = QPushButton("Resume Sale")
        self.btn_recall.setObjectName("primaryButton")
        self.btn_recall.clicked.connect(self.on_confirm)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_recall)
        layout.addLayout(buttons)

        self.table.doubleClicked.connect(self.on_confirm)
        if held_sales:
            self.table.selectRow(0)

    def on_confirm(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.held_ids):
            self.selected_hold_id = self.held_ids[row]
            self.accept()
