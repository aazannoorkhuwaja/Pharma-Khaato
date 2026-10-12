"""Shared responsive helpers for desktop views and dialogs."""

from PySide6.QtWidgets import QApplication, QDialog, QSizePolicy, QWidget

from ui.theme.layout import LayoutMetrics
from ui.theme.theme_manager import ThemeManager


def flexible_side_panel(widget: QWidget, minimum: int = None, maximum: int = None) -> QWidget:
    """Make a side panel flex instead of using a fixed pixel width."""
    scale = min(1.30, ThemeManager.get_font_scale())
    minimum = int((minimum or LayoutMetrics.SIDE_PANEL_MIN) * scale)
    maximum = int((maximum or LayoutMetrics.SIDE_PANEL_MAX) * scale)
    widget.setMinimumWidth(minimum)
    widget.setMaximumWidth(maximum)
    widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    return widget


def flexible_primary_panel(widget: QWidget, minimum: int = 420) -> QWidget:
    """Give the primary work area priority while retaining horizontal scrolling."""
    widget.setMinimumWidth(minimum)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return widget


def configure_dialog(dialog: QDialog, preferred_width: int, preferred_height: int,
                     minimum_width: int = 360, minimum_height: int = 260) -> None:
    """Size dialogs against the actual available desktop instead of hard-coding them.

    The dialog keeps a useful minimum size but is clamped to the current screen,
    preventing controls from falling below the task bar on 768p or scaled displays.
    """
    dialog.setSizeGripEnabled(True)
    scale = min(1.25, ThemeManager.get_font_scale())
    preferred_width = int(preferred_width * scale)
    preferred_height = int(preferred_height * scale)
    minimum_width = int(minimum_width * min(scale, 1.15))
    minimum_height = int(minimum_height * min(scale, 1.15))
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen is None:
        dialog.setMinimumSize(minimum_width, minimum_height)
        dialog.resize(preferred_width, preferred_height)
        return

    area = screen.availableGeometry()
    max_w = max(minimum_width, area.width() - LayoutMetrics.DIALOG_MARGIN)
    max_h = max(minimum_height, area.height() - LayoutMetrics.DIALOG_MARGIN)
    width = min(preferred_width, max_w)
    height = min(preferred_height, max_h)
    dialog.setMinimumSize(min(minimum_width, width), min(minimum_height, height))
    dialog.resize(width, height)


def semantic_label(label, role: str, *, color: str = None, weight: int = None) -> None:
    """Apply semantic typography through global QSS, with optional color/weight only."""
    role_to_object = {
        "title": "h1",
        "section": "h2",
        "subtitle": "subtitle",
        "caption": "caption",
        "metric": "metric",
        "metricLarge": "metricLarge",
    }
    label.setObjectName(role_to_object.get(role, role))
    declarations = []
    if color:
        declarations.append(f"color: {color}")
    if weight:
        declarations.append(f"font-weight: {weight}")
    if declarations:
        label.setStyleSheet("; ".join(declarations) + ";")
