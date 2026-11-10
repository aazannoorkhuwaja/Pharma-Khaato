"""Small native vector icons for the reference pharmacy interface."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

_PATHS = {
    'pos': '<path d="M3 4h2l3 12h11l3-9H6M9 20h.01M18 20h.01"/>',
    'customers': '<circle cx="9" cy="7" r="3"/><path d="M2 21v-3a7 7 0 0 1 14 0v3M17 4a3 3 0 0 1 0 6M19 14a6 6 0 0 1 3 5v2"/>',
    'khatoo': '<circle cx="8" cy="7" r="3"/><path d="M1 21v-3a7 7 0 0 1 10-6"/><rect x="13" y="13" width="10" height="8" rx="2"/><path d="M13 16h10"/>',
    'inventory': '<path d="m12 2 10 5v10l-10 5-10-5V7Zm-10 5 10 5 10-5M12 12v10M7 4.5l10 5"/>',
    'cash_session': '<rect x="3" y="12" width="18" height="10" rx="2"/><path d="M6 12V4h12v8M8 7h8M7 16h2m3 0h2m3 0h1M7 19h10"/>',
    'reports': '<path d="M2 22h21M4 22V12h4v10M11 22V7h4v15M18 22V2h4v20"/>',
    'settings': '<circle cx="12" cy="12" r="4"/><path d="m9 2 6 0 1 3 3 1 3 3v6l-3 1-1 3-3 3H9l-1-3-3-1-3-3V9l3-1 1-3Z"/>',
    'returns': '<path d="M4 8h10a7 7 0 1 1-6 11M4 8l5-5M4 8l5 5"/>',
    'search': '<circle cx="10" cy="10" r="7"/><path d="m15 15 7 7"/>',
    'hold': '<circle cx="12" cy="12" r="10"/><path d="M9 8v8M15 8v8"/>',
    'resume': '<path d="m8 4 12 8-12 8Z"/>',
    'print': '<path d="M6 8V2h12v6M6 17H2V8h20v9h-4M6 14h12v8H6ZM17 11h2"/>',
    'cash': '<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M5 9v6M19 9v6"/>',
    'card': '<rect x="2" y="4" width="20" height="16" rx="3"/><path d="M2 9h20M6 15h4"/>',
    'check': '<circle cx="12" cy="12" r="10"/><path d="m7 12 3 3 7-7"/>',
}


def icon(name, color='#10203C', size=22):
    body = _PATHS.get(name, _PATHS['cash'])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


class PharmacyMark(QWidget):
    """Decorative storefront drawn natively; no screenshot text or fake status."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(116)
        self.setMaximumHeight(140)
        self.setAccessibleName('Pharma Khaato — POS for Pharmacies')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor('#91A6BE'))
        cx = self.width() / 2
        p.drawRoundedRect(QRectF(cx - 23, 33, 46, 32), 2, 2)
        p.drawRect(QRectF(cx - 6, 45, 12, 20))
        p.drawRect(QRectF(cx - 16, 41, 7, 10))
        p.drawRect(QRectF(cx + 9, 41, 7, 10))
        p.drawRoundedRect(QRectF(cx - 29, 22, 58, 13), 3, 3)
        p.drawLine(int(cx), 5, int(cx), 18)
        p.drawLine(int(cx - 6), 11, int(cx + 6), 11)
        p.drawText(QRectF(0, 72, self.width(), 22), Qt.AlignCenter, 'Pharma-Khaato')
        p.drawText(QRectF(0, 94, self.width(), 20), Qt.AlignCenter, 'POS for Pharmacies')
        p.end()
