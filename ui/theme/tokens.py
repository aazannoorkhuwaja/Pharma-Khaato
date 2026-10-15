"""
Pharma-Khaato Design System — Dynamic Immutable Design Tokens
Single source of truth for color, spacing, radius, and typography.
Default theme is Light Mode.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Palette:
    BG_DARK: str
    BG_GRADIENT: str
    SURFACE_BASE: str
    SURFACE_ELEVATED: str
    SURFACE_GLASS: str
    BORDER_SUBTLE: str
    BORDER_STRONG: str
    BORDER_FOCUS: str
    TEXT_PRIMARY: str
    TEXT_SECONDARY: str
    TEXT_MUTED: str
    ACCENT: str
    ACCENT_HOVER: str
    ACCENT_LIGHT: str
    SUCCESS: str
    WARNING: str
    DANGER: str
    INFO: str

LIGHT_PALETTE = Palette(
    # Premium light: warm porcelain canvas, true-white cards, ink text,
    # emerald accent — high contrast without harshness.
    BG_DARK="#EEF2F7",
    BG_GRADIENT="qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F7F9FC, stop:1 #E8EDF4)",
    SURFACE_BASE="#FFFFFF",
    SURFACE_ELEVATED="#FBFCFE",
    SURFACE_GLASS="rgba(255, 255, 255, 0.92)",
    BORDER_SUBTLE="#DCE3EC",
    BORDER_STRONG="#AAB6C6",
    BORDER_FOCUS="#0E9F6E",
    TEXT_PRIMARY="#101828",
    TEXT_SECONDARY="#3A4556",
    TEXT_MUTED="#69758A",
    ACCENT="#0E9F6E",
    ACCENT_HOVER="#0B7E57",
    ACCENT_LIGHT="#E3F5EE",
    SUCCESS="#0E9F6E",
    WARNING="#B45309",
    DANGER="#DC2626",
    INFO="#1D4ED8",
)

DARK_PALETTE = Palette(
    BG_DARK="#0B0E14",
    BG_GRADIENT="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090B10, stop:1 #131722)",
    SURFACE_BASE="#151922",
    SURFACE_ELEVATED="#1F2534",
    SURFACE_GLASS="#151922",
    BORDER_SUBTLE="#2D3546",
    BORDER_STRONG="#404B62",
    BORDER_FOCUS="#10B981",
    TEXT_PRIMARY="#F9FAFB",
    TEXT_SECONDARY="#D1D5DB",
    TEXT_MUTED="#9CA3AF",
    ACCENT="#10B981",
    ACCENT_HOVER="#059669",
    ACCENT_LIGHT="#064E3B",
    SUCCESS="#10B981",
    WARNING="#F59E0B",
    DANGER="#EF4444",
    INFO="#3B82F6",
)

class ThemeTokensMeta(type):
    @property
    def BG_DARK(cls) -> str: return cls._active_palette.BG_DARK
    @property
    def BG_GRADIENT(cls) -> str: return cls._active_palette.BG_GRADIENT
    @property
    def SURFACE_BASE(cls) -> str: return cls._active_palette.SURFACE_BASE
    @property
    def SURFACE_ELEVATED(cls) -> str: return cls._active_palette.SURFACE_ELEVATED
    @property
    def SURFACE_GLASS(cls) -> str: return cls._active_palette.SURFACE_GLASS
    @property
    def BORDER_SUBTLE(cls) -> str: return cls._active_palette.BORDER_SUBTLE
    @property
    def BORDER_STRONG(cls) -> str: return cls._active_palette.BORDER_STRONG
    @property
    def BORDER_FOCUS(cls) -> str: return cls._active_palette.BORDER_FOCUS
    @property
    def TEXT_PRIMARY(cls) -> str: return cls._active_palette.TEXT_PRIMARY
    @property
    def TEXT_SECONDARY(cls) -> str: return cls._active_palette.TEXT_SECONDARY
    @property
    def TEXT_MUTED(cls) -> str: return cls._active_palette.TEXT_MUTED
    @property
    def ACCENT(cls) -> str: return cls._active_palette.ACCENT
    @property
    def ACCENT_HOVER(cls) -> str: return cls._active_palette.ACCENT_HOVER
    @property
    def ACCENT_LIGHT(cls) -> str: return cls._active_palette.ACCENT_LIGHT
    @property
    def SUCCESS(cls) -> str: return cls._active_palette.SUCCESS
    @property
    def WARNING(cls) -> str: return cls._active_palette.WARNING
    @property
    def DANGER(cls) -> str: return cls._active_palette.DANGER
    @property
    def INFO(cls) -> str: return cls._active_palette.INFO
    @property
    def DARK_BG_DARK(cls) -> str: return DARK_PALETTE.BG_DARK
    @property
    def DARK_TEXT_PRIMARY(cls) -> str: return DARK_PALETTE.TEXT_PRIMARY

class ThemeTokens(metaclass=ThemeTokensMeta):
    _active_palette = LIGHT_PALETTE

    FONT_FAMILY = "'Segoe UI', 'Inter', Arial, sans-serif"

    SPACE_XS  = 4
    SPACE_SM  = 8
    SPACE_MD  = 12
    SPACE_LG  = 16
    SPACE_XL  = 24
    SPACE_2XL = 32

    FONT_SIZE_LABEL = 11
    FONT_SIZE_BODY  = 13
    FONT_SIZE_MONO  = 13
    FONT_SIZE_H2    = 16
    FONT_SIZE_H1    = 22

    RADIUS_SM = 6
    RADIUS_MD = 8
    RADIUS_LG = 10
    RADIUS_XL = 14

    @classmethod
    def set_palette(cls, mode: str):
        cls._active_palette = DARK_PALETTE if mode == "dark" else LIGHT_PALETTE

    @classmethod
    def palette(cls) -> Palette:
        return cls._active_palette
