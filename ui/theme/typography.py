"""
Pharma-Khaato Design System — Typography Scale
Defines font scale, weights, and helper functions for PySide6 QLabels.
"""

from PySide6.QtGui import QFont

class Typography:
    FAMILY = "Segoe UI, Inter, -apple-system, sans-serif"

    # Font Sizes
    SIZE_H1 = 22
    SIZE_H2 = 16
    SIZE_H3 = 14
    SIZE_BODY = 13
    SIZE_CAPTION = 11
    SIZE_SMALL = 10

    @staticmethod
    def h1_font() -> QFont:
        f = QFont("Segoe UI", Typography.SIZE_H1)
        f.setWeight(QFont.Weight.ExtraBold)
        return f

    @staticmethod
    def h2_font() -> QFont:
        f = QFont("Segoe UI", Typography.SIZE_H2)
        f.setWeight(QFont.Weight.Bold)
        return f

    @staticmethod
    def body_font() -> QFont:
        f = QFont("Segoe UI", Typography.SIZE_BODY)
        f.setWeight(QFont.Weight.Normal)
        return f

    @staticmethod
    def caption_font() -> QFont:
        f = QFont("Segoe UI", Typography.SIZE_CAPTION)
        f.setWeight(QFont.Weight.Normal)
        return f
