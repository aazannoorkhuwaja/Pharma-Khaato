"""
Pharma-Khaato Design Tokens, Color Palettes & Font System
Bridge file mapping legacy imports directly to ThemeTokens and ThemeManager dynamically.
"""

from ui.theme.tokens import ThemeTokens

class DynamicColorsDict(dict):
    def __getitem__(self, key):
        mapping = {
            "bg_main": ThemeTokens.BG_DARK,
            "bg_card": ThemeTokens.SURFACE_BASE,
            "sidebar": ThemeTokens.SURFACE_ELEVATED,
            "sidebar_hover": ThemeTokens.ACCENT_LIGHT,
            "sidebar_text": ThemeTokens.TEXT_PRIMARY,
            "sidebar_active": ThemeTokens.ACCENT,
            "primary": ThemeTokens.ACCENT,
            "primary_hover": ThemeTokens.ACCENT_HOVER,
            "secondary": ThemeTokens.TEXT_MUTED,
            "success": ThemeTokens.SUCCESS,
            "warning": ThemeTokens.WARNING,
            "danger": ThemeTokens.DANGER,
            "text_dark": ThemeTokens.TEXT_PRIMARY,
            "text_muted": ThemeTokens.TEXT_MUTED,
            "border": ThemeTokens.BORDER_SUBTLE,
            "border_focus": ThemeTokens.BORDER_FOCUS,
        }
        return mapping.get(key, "#059669")

    def get(self, key, default=None):
        val = self[key]
        return val if val is not None else default

COLORS = DynamicColorsDict()
HIGH_CONTRAST_COLORS = COLORS

_FONT_FAMILY = "'Segoe UI', 'Inter', Arial, sans-serif"

FONTS_NORMAL = {
    "title_large": (_FONT_FAMILY, 18, "bold"),
    "title_medium": (_FONT_FAMILY, 14, "bold"),
    "header_sub": (_FONT_FAMILY, 11, "bold"),
    "body_bold": (_FONT_FAMILY, 10, "bold"),
    "body": (_FONT_FAMILY, 10),
    "small": (_FONT_FAMILY, 9),
    "badge": (_FONT_FAMILY, 9, "bold"),
}

FONTS_LARGE = {
    "title_large": (_FONT_FAMILY, 22, "bold"),
    "title_medium": (_FONT_FAMILY, 18, "bold"),
    "header_sub": (_FONT_FAMILY, 14, "bold"),
    "body_bold": (_FONT_FAMILY, 13, "bold"),
    "body": (_FONT_FAMILY, 13),
    "small": (_FONT_FAMILY, 11),
    "badge": (_FONT_FAMILY, 11, "bold"),
}

FONTS = FONTS_NORMAL
