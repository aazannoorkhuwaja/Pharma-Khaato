"""High-visibility semantic status pill."""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class BadgePill(QLabel):
    TYPE_SUCCESS = "success"
    TYPE_WARNING = "warning"
    TYPE_DANGER = "danger"
    TYPE_INFO = "info"

    def __init__(self, text: str = "", pill_type: str = TYPE_INFO, parent=None):
        super().__init__(text, parent)
        self.setObjectName("badgePill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_pill_type(pill_type)

    def set_pill_type(self, pill_type: str):
        self.setProperty("pillType", pill_type)
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)
        self.update()
