"""Reusable semantic buttons.

Sizing and colors are global theme concerns.  These classes only declare the
button's semantic role so runtime font/interface scaling works everywhere.
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt


class PrimaryButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class SecondaryButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class DangerButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("dangerButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
