"""Shared business-table ergonomics and clipping prevention."""

from PySide6.QtCore import Qt

from ui.theme.layout import LayoutMetrics
from ui.theme.theme_manager import ThemeManager


def polish_table(table, min_row_height: int = 0) -> None:
    """Apply consistent, scalable table behaviour across the product.

    Tables keep readable row heights at every accessibility scale, reserve real
    scrollbar space, elide long text instead of overlapping adjacent columns,
    and always expose horizontal scrolling when the dataset needs it.
    """
    if table is None:
        return

    scale = ThemeManager.get_font_scale()
    header = table.horizontalHeader()
    if header is not None:
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(LayoutMetrics.scaled(64, scale))
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

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
