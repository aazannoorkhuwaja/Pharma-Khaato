from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex


class ProductCatalogModel(QAbstractTableModel):
    """Virtualized, cashier-friendly product search result model.

    Backend rows retain the selected FEFO batch identifier, but the routine
    counter view shows only information that helps choose a medicine: product,
    expiry, available stock, and price.
    """

    HEADERS = ["Product", "Expiry", "In Stock", "Price"]

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

        column = index.column()
        row_data = self._formatted_rows[index.row()]

        if role == Qt.DisplayRole:
            return row_data[column]
        if role == Qt.TextAlignmentRole:
            if column in (2, 3):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        return None

    def update_data(self, results: list):
        self.beginResetModel()
        self._raw_data = results or []
        self._formatted_rows = []
        for item in self._raw_data:
            _product_id, product_name, price, _batch_id, batch_qty, batch_expiry = item
            self._formatted_rows.append(
                (
                    str(product_name),
                    str(batch_expiry),
                    str(batch_qty),
                    f"Rs. {float(price):.2f}",
                )
            )
        self.endResetModel()

    def get_raw_item(self, row: int):
        if 0 <= row < len(self._raw_data):
            return self._raw_data[row]
        return None
