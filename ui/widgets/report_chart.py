"""Native, theme-aware report charts driven only by supplied service values."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import QWidget, QSizePolicy
from ui.theme.tokens import ThemeTokens


class ReportChart(QWidget):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.values = []
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName('Sales trend' if kind == 'trend' else 'Payment method distribution')

    def set_values(self, values):
        self.values = [(str(label), float(value)) for label, value in values]
        self.setAccessibleDescription('; '.join(f'{label}: Rs. {value:,.2f}' for label, value in self.values))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(ThemeTokens.TEXT_SECONDARY))
        if not self.values:
            p.drawText(self.rect(), Qt.AlignCenter, 'Report data unavailable')
        elif self.kind == 'trend':
            area = QRectF(48, 14, max(1, self.width()-64), max(1, self.height()-44))
            low = min(0, min(value for _, value in self.values))
            high = max(1, max(value for _, value in self.values))
            for i in range(4):
                y = area.top() + area.height()*i/3
                p.setPen(QColor(ThemeTokens.BORDER_SUBTLE))
                p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
                p.setPen(QColor(ThemeTokens.TEXT_MUTED))
                p.drawText(QRectF(0,y-8,44,16), Qt.AlignRight, f'{high-(high-low)*i/3:,.0f}')
            path = QPainterPath()
            for i, (label, value) in enumerate(self.values):
                point = QPointF(area.left()+i*area.width()/max(1,len(self.values)-1), area.bottom()-(value-low)/(high-low)*area.height())
                if i == 0: path.moveTo(point)
                else: path.lineTo(point)
                p.setPen(QColor(ThemeTokens.TEXT_MUTED))
                if i in (0,len(self.values)//2,len(self.values)-1):
                    p.drawText(QRectF(max(0,min(self.width()-52,point.x()-26)),area.bottom()+8,52,20), Qt.AlignCenter,label)
            p.setPen(QPen(QColor(ThemeTokens.ACCENT),2))
            p.drawPath(path)
        else:
            values = [(label,max(0,value)) for label,value in self.values]
            total = sum(value for _,value in values)
            diameter = min(self.height()-20,self.width()*.43)
            rect = QRectF(8,10,diameter,diameter)
            colors = [ThemeTokens.ACCENT,'#57B983','#F4C657','#6D9CD8','#A192CE','#93A4B8']
            start = 90*16
            if total:
                for index,(label,value) in enumerate(values):
                    p.setPen(QPen(QColor(colors[index%len(colors)]),18))
                    span = -round(value/total*360*16)
                    p.drawArc(rect.adjusted(12,12,-12,-12),start,span)
                    start += span
            else:
                p.setPen(QPen(QColor(ThemeTokens.BORDER_SUBTLE),18))
                p.drawEllipse(rect.adjusted(12,12,-12,-12))
            p.setPen(QColor(ThemeTokens.TEXT_PRIMARY))
            p.drawText(rect, Qt.AlignCenter, f'Rs.\n{total:,.0f}')
            for index,(label,value) in enumerate(values):
                y = 12+index*23
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(colors[index%len(colors)]))
                p.drawEllipse(QRectF(diameter+20,y+4,7,7))
                p.setPen(QColor(ThemeTokens.TEXT_SECONDARY))
                p.drawText(QRectF(diameter+34,y,self.width()-diameter-38,22),Qt.AlignLeft,f'{label}  {value/total*100 if total else 0:.0f}%')
        p.end()
