"""Reusable inline status surface for loading, empty, and recoverable error states."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from ui.widgets.semantic_style import set_tone


class InlineState(QFrame):
    """Compact state message that keeps feedback in context instead of modal.

    Use ``show_loading`` while asynchronous work is running, ``show_empty``
    when a successful query has no rows, and ``show_error`` for recoverable
    failures. A retry action is optional and keyboard-focusable.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inlineState")
        self.setAccessibleName("Status")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(self.label, 1)

        self.retry_button = QPushButton("Try Again")
        self.retry_button.setProperty("compact", True)
        self.retry_button.setAccessibleName("Try again")
        self.retry_button.hide()
        layout.addWidget(self.retry_button)
        self.hide()

    def _set(self, text: str, tone: str, retry: Callable | None = None):
        self.label.setText(str(text))
        set_tone(self.label, tone, "semibold" if tone in {"danger", "warning"} else None)
        try:
            self.retry_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        if retry is not None:
            self.retry_button.clicked.connect(retry)
            self.retry_button.show()
        else:
            self.retry_button.hide()
        self.show()

    def show_loading(self, text: str = "Loading…"):
        self._set(text, "muted")

    def show_empty(self, text: str):
        self._set(text, "muted")

    def show_error(self, text: str, retry: Callable | None = None):
        self._set(text, "danger", retry)

    def clear(self):
        self.hide()
        self.label.clear()
        self.retry_button.hide()
