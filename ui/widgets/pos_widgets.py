"""
POS widgets extracted from the POS screen for maintainability:
search input, search results table, cart table, and recall-sale dialog.
"""

from PySide6.QtWidgets import (
    QLineEdit, QTableView, QTableWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QWidget, QPushButton, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from ui.theme.tokens import ThemeTokens
from ui.widgets.responsive import configure_dialog
from ui.widgets.table_polish import polish_table


class SearchLineEdit(QLineEdit):
    """Custom QLineEdit providing Key_Down arrow navigation to Search Results Table."""
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
    """Custom virtualized QTableView providing Return (select) & Escape (cancel) key navigation."""
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
            index = self.model().index(row, 0)
            self.setCurrentIndex(index)

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
    """Custom QTableWidget providing Delete, +, - key bindings to remove/adjust highlighted cart rows."""
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
    """Dialog for picking a held sale when multiple held sales exist."""
    def __init__(self, held_sales, parent=None):
        super().__init__(parent)
        self.selected_hold_id = None
        self.setWindowTitle("Resume Held Sale")
        configure_dialog(self, 680, 440, minimum_width=500, minimum_height=340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_title = QLabel("Held Sales")
        lbl_title.setObjectName("h2")
        lbl_title.setStyleSheet(f" font-weight: 800; color: {ThemeTokens.ACCENT};")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Choose the held sale you want to continue.")
        lbl_sub.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(lbl_sub)

        self.table = QTableWidget(len(held_sales), 5)
        self.table.setHorizontalHeaderLabels(["Hold #", "Held At", "Customer", "Items", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        polish_table(self.table)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.held_ids = []
        for row, item in enumerate(held_sales):
            h_id, h_time, c_id, e_id, cart_json, note = item
            self.held_ids.append(h_id)
            try:
                cart_data = json.loads(cart_json)
                qty_sum = sum(i.get("qty", 1) for i in cart_data)
                tot_sum = sum(i.get("subtotal", 0.0) for i in cart_data)
            except Exception:
                qty_sum = 0
                tot_sum = 0.0

            self.table.setItem(row, 0, QTableWidgetItem(f"#{h_id}"))
            self.table.setItem(row, 1, QTableWidgetItem(str(h_time)))
            self.table.setItem(row, 2, QTableWidgetItem(str(c_id)))
            self.table.setItem(row, 3, QTableWidgetItem(str(qty_sum)))
            self.table.setItem(row, 4, QTableWidgetItem(f"Rs. {tot_sum:.2f}"))

        layout.addWidget(self.table, 1)

        btn_box = QHBoxLayout()
        self.btn_recall = QPushButton("Resume Sale")
        self.btn_recall.setObjectName("primaryButton")
        self.btn_recall.clicked.connect(self.on_confirm)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_recall)
        layout.addLayout(btn_box)

        self.table.doubleClicked.connect(self.on_confirm)
        if len(held_sales) > 0:
            self.table.selectRow(0)

    def on_confirm(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.held_ids):
            self.selected_hold_id = self.held_ids[row]
            self.accept()


