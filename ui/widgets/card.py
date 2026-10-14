from PySide6.QtWidgets import QFrame, QVBoxLayout, QSizePolicy

from ui.theme.tokens import ThemeTokens


class Card(QFrame):
    """Standard surface container.

    Default cards intentionally do *not* own colors/font sizes in a local style
    sheet.  The global ThemeManager remains the single source of truth, which
    allows dark mode and interface scaling to update every screen consistently.
    """

    def __init__(self, parent=None, bg_color: str = None, border_color: str = None,
                 radius: int = None, layout=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # Rare custom cards may still opt into explicit colors.
        if bg_color is not None or border_color is not None or radius is not None:
            bg = bg_color or ThemeTokens.SURFACE_ELEVATED
            border = border_color or ThemeTokens.BORDER_SUBTLE
            rad = radius if radius is not None else ThemeTokens.RADIUS_MD
            self.setStyleSheet(
                f"QFrame#card {{ background-color: {bg}; border: 1px solid {border}; "
                f"border-radius: {rad}px; }}"
            )

        if layout is not None:
            self._layout = layout
            self.setLayout(self._layout)
        else:
            self._layout = QVBoxLayout()
            self._layout.setContentsMargins(14, 14, 14, 14)
            self._layout.setSpacing(10)
            self.setLayout(self._layout)

    def addWidget(self, widget, stretch=0, alignment=None):
        if alignment is not None:
            self._layout.addWidget(widget, stretch, alignment)
        else:
            self._layout.addWidget(widget, stretch)

    def addLayout(self, layout, stretch=0):
        self._layout.addLayout(layout, stretch)


__all__ = ["Card"]
