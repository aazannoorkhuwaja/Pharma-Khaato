"""Compact keyboard shortcut hint with responsive label collapse."""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class HotkeyBadge(QLabel):
    def __init__(self, shortcut_text: str = "", label: str = "", parent=None):
        super().__init__(parent)
        self.shortcut_text = shortcut_text
        self.label_text = label
        self.setObjectName("hotkeyBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_compact(False)

    def set_compact(self, compact: bool):
        if compact or not self.label_text:
            self.setText(f"[{self.shortcut_text}]")
        else:
            self.setText(f"[{self.shortcut_text}] {self.label_text}")
        self.setToolTip(
            f"{self.shortcut_text} — {self.label_text}" if self.label_text else self.shortcut_text
        )
