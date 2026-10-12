"""Shared business-table ergonomics and clipping prevention."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from ui.theme.layout import LayoutMetrics
from ui.theme.theme_manager import ThemeManager


# Database keys are useful to the application, but they are not useful visual
# information for a cashier or pharmacy owner completing a routine task.
_INTERNAL_COLUMN_LABELS = {
    "id",
    "ref #",
    "record id",
    "employee id",
    "movement id",
    "shift #",
}

_ACTION_COLUMN_LABELS = {
    "action",
    "payment",
}


def polish_table(table, min_row_height: int = 0, hide_internal_keys: bool = True) -> None:
    """Apply consistent, scalable table behaviour across the product.

    Tables keep readable row heights at every accessibility scale, reserve real
    scrollbar space, elide long text instead of overlapping adjacent columns,
    and expose horizontal scrolling only when the dataset needs it.

    Routine screens hide exact database-key columns while preserving those
    values in the table model for workflow callbacks. Action columns stay
    compact instead of stretching into full-width button bars.
    """
    if table is None:
        return

    scale = ThemeManager.get_font_scale()
    header = table.horizontalHeader()
    if header is not None:
        # Do not stretch the final column globally. Screens already choose
        # which descriptive column should stretch; the last column is commonly
        # a compact action such as Pay/Add Stock.
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(LayoutMetrics.scaled(64, scale))
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        for column in range(table.columnCount()):
            item = table.horizontalHeaderItem(column)
            label = item.text().strip().lower() if item is not None else ""

            if hide_internal_keys and label in _INTERNAL_COLUMN_LABELS:
                table.setColumnHidden(column, True)
                continue

            if label in _ACTION_COLUMN_LABELS:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setAlternatingRowColors(True)

    base_height = min_row_height or LayoutMetrics.TABLE_ROW_HEIGHT
    vh = table.verticalHeader()
    if vh is not None:
        row_height = LayoutMetrics.scaled(base_height, scale)
        vh.setDefaultSectionSize(row_height)
        vh.setMinimumSectionSize(row_height)
