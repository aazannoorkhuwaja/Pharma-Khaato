"""Reusable responsive screen header."""

from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QVBoxLayout, QLabel, QWidget

from ui.widgets.glass_card import Card


class ScreenHeader(Card):
    """Screen title, descriptive copy and contextual status/actions.

    At narrow widths the action/pill region moves below the title so text never
    gets squeezed to a few characters on 1024px laptops or accessibility scale.
    """

    BREAKPOINT = 760

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)

        self.header_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.header_layout.setSpacing(12)
        self.addLayout(self.header_layout)

        self.title_box = QVBoxLayout()
        self.title_box.setSpacing(3)
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("h1")
        self.lbl_title.setWordWrap(True)
        self.title_box.addWidget(self.lbl_title)

        self.lbl_subtitle = None
        if subtitle:
            self.lbl_subtitle = QLabel(subtitle)
            self.lbl_subtitle.setObjectName("subtitle")
            self.lbl_subtitle.setWordWrap(True)
            self.title_box.addWidget(self.lbl_subtitle)

        self.header_layout.addLayout(self.title_box, 1)

        self.actions_widget = QWidget()
        self.pills_layout = QHBoxLayout(self.actions_widget)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(8)
        self.header_layout.addWidget(self.actions_widget, 0)

    def add_pill(self, widget):
        self.pills_layout.addWidget(widget)

    def add_widget(self, widget):
        self.pills_layout.addWidget(widget)

    def resizeEvent(self, event):
        narrow = event.size().width() < self.BREAKPOINT
        desired = (QBoxLayout.Direction.TopToBottom if narrow
                   else QBoxLayout.Direction.LeftToRight)
        if self.header_layout.direction() != desired:
            self.header_layout.setDirection(desired)
            self.actions_widget.setMaximumWidth(16777215)
        super().resizeEvent(event)
