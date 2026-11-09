"""Accessible native tender button with vertically arranged icon and label."""
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QPushButton, QStylePainter, QStyleOptionButton, QStyle


class PaymentTile(QPushButton):
    def sizeHint(self):
        size = super().sizeHint()
        return QSize(max(66, self.fontMetrics().horizontalAdvance(self.text()) + 14), max(58, size.height()))

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ''
        option.icon = type(self.icon())()
        painter.drawControl(QStyle.CE_PushButton, option)
        icon_rect = QRect((self.width() - 20) // 2, 7, 20, 20)
        self.icon().paint(painter, icon_rect)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.ButtonText if self.isEnabled() else QPalette.PlaceholderText))
        text = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, self.width() - 6)
        painter.drawText(QRect(3, 28, self.width() - 6, self.height() - 30), Qt.AlignCenter, text)
