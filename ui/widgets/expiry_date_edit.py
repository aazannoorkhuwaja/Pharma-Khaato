"""Blank printed expiry with a calendar that starts in the current month."""
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QCalendarWidget, QDateEdit


class _ExpiryCalendar(QCalendarWidget):
    def showEvent(self, event):
        super().showEvent(event)
        if self.selectedDate() == QDate(1900, 1, 1):
            today = QDate.currentDate()
            self.setCurrentPage(today.year(), today.month())


class PrintedExpiryEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setCalendarWidget(_ExpiryCalendar(self))
        self.setMinimumDate(QDate(1900, 1, 1))
        self.setSpecialValueText('Choose printed expiry')
        self.setDate(self.minimumDate())
        self.setDisplayFormat('dd/MM/yyyy')
