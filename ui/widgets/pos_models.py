from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex

class ProductCatalogModel(QAbstractTableModel):
    """
    High-performance virtualized model for product search results.
    Avoids widget allocation per cell and formats strings lazily for 60 FPS scrolling.
    """
    HEADERS = ["Product Name", "Batch #", "Expiry Date", "Stock", "Price"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_data = []
        self._formatted_rows = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._formatted_rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._formatted_rows)):
            return None

        col = index.column()
        row_data = self._formatted_rows[index.row()]

        if role == Qt.DisplayRole:
            return row_data[col]
        elif role == Qt.TextAlignmentRole:
            if col in (3, 4):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def update_data(self, results: list):
        self.beginResetModel()
        self._raw_data = results or []
        self._formatted_rows = []
        for item in self._raw_data:
            p_id, p_name, p_price, b_id, b_qty, b_exp = item
            self._formatted_rows.append((
                str(p_name),
                f"Batch #{b_id}",
                str(b_exp),
                str(b_qty),
                f"Rs. {float(p_price):.2f}"
            ))
        self.endResetModel()

    def get_raw_item(self, row: int):
        if 0 <= row < len(self._raw_data):
            return self._raw_data[row]
        return None
