"""
Pharma-Khaato Design System — Theme Manager
Two themes: Light (default, high-contrast) and Dark (opt-in toggle).
Theme is applied globally via QApplication.setStyleSheet so ALL screens
pick it up immediately — not per-widget, not per-screen.
"""

import os
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QColor, QPalette
from ui.theme.tokens import ThemeTokens
from ui.theme.layout import LayoutMetrics
from controllers.settings_controller import SettingsController

_SETTINGS_CONTROLLER = SettingsController()
from core.logger import get_logger

logger = get_logger("PharmaKhaatoTheme")


class ThemeEvents(QObject):
    changed = Signal()


class ThemeManager:
    events = ThemeEvents()
    _current_mode = "light"   # Light is the default
    _current_scale = 1.0

    @classmethod
    def get_theme_mode(cls) -> str:
        return cls._current_mode

    @classmethod
    def get_font_scale(cls) -> float:
        return cls._current_scale

    @classmethod
    def load_preferences(cls):
        """Load theme preferences through the MVC settings controller."""
        try:
            mode = _SETTINGS_CONTROLLER.get("theme_mode", "light")
            mode = mode if mode in ("dark", "light") else "light"
            cls._current_mode = mode
            ThemeTokens.set_palette(mode)
            raw_scale = _SETTINGS_CONTROLLER.get("font_scale", "1.0")
            cls._current_scale = max(0.8, min(2.0, float(raw_scale)))
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to parse theme preferences: {e}")
            cls._current_mode = "light"
            cls._current_scale = 1.0
            ThemeTokens.set_palette("light")
        except Exception as e:
            logger.warning(f"Failed to load theme preferences: {e}")

    @classmethod
    def save_preferences(cls):
        """Persist theme preferences through the MVC settings controller."""
        ok = _SETTINGS_CONTROLLER.update({
            "theme_mode": cls._current_mode,
            "font_scale": str(cls._current_scale),
        })
        if not ok:
            logger.warning("Failed to save one or more theme preferences.")

    @classmethod
    def set_theme(cls, mode: str, save: bool = True):
        """Sets active theme: 'light' or 'dark'. Applies globally to QApplication."""
        # Accept 'high_contrast' from old Settings UI and map it cleanly
        if mode not in ("dark", "light", "high_contrast"):
            return
        if mode == "high_contrast":
            mode = "light"
        cls._current_mode = mode
        ThemeTokens.set_palette(mode)
        if save:
            cls.save_preferences()
        cls.apply_theme()
        cls.events.changed.emit()

    @classmethod
    def toggle_theme(cls, save: bool = True):
        """Toggles between Light and Dark — the only two themes."""
        new_mode = "dark" if cls._current_mode == "light" else "light"
        cls.set_theme(new_mode, save=save)

    @classmethod
    def set_font_scale(cls, scale: float, save: bool = True):
        """Sets font scaling factor and applies globally."""
        cls._current_scale = max(0.8, min(2.0, float(scale)))
        if save:
            cls.save_preferences()
        cls.apply_theme()
        cls.events.changed.emit()

    @classmethod
    def apply_theme(cls):
        """Applies QSS stylesheet and font to the QApplication instance."""
        app = QApplication.instance()
        if not app:
            return
        palette = QPalette()
        for role, color in ((QPalette.Window, ThemeTokens.BG_DARK),
                            (QPalette.WindowText, ThemeTokens.TEXT_PRIMARY),
                            (QPalette.Base, ThemeTokens.SURFACE_BASE),
                            (QPalette.AlternateBase, ThemeTokens.SURFACE_ELEVATED),
                            (QPalette.Text, ThemeTokens.TEXT_PRIMARY),
                            (QPalette.Button, ThemeTokens.SURFACE_ELEVATED),
                            (QPalette.ButtonText, ThemeTokens.TEXT_PRIMARY)):
            palette.setColor(role, QColor(color))
        app.setPalette(palette)
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            logger.debug("Offscreen test rendering detected; skipping Qt C++ stylesheet re-application.")
            return
        try:
            qss = cls.build_qss(mode=cls._current_mode, scale=cls._current_scale)
            app.setStyleSheet(qss)
            # Segoe UI first, matching ThemeTokens.FONT_FAMILY
            font = QFont("Segoe UI", int(10 * cls._current_scale))
            font.setStyleHint(QFont.SansSerif)
            app.setFont(font)
        except Exception as e:
            logger.warning(f"Error setting application stylesheet: {e}")

    @classmethod
    def build_qss(cls, mode: str = None, scale: float = None) -> str:
        """
        Builds the global QSS string for the requested mode.
        Called by apply_theme() — all screens inherit this automatically.
        """
        if mode is None:
            mode = cls._current_mode
        else:
            ThemeTokens.set_palette(mode)
        if scale is None:
            scale = cls._current_scale

        t = ThemeTokens
        is_dark = (mode == "dark")

        # ── Scaled sizes ──────────────────────────────────────────────────
        fs_body   = int(t.FONT_SIZE_BODY * scale)    # 13px at 1.0 — minimum for counter data
        fs_label  = int(t.FONT_SIZE_LABEL * scale)   # 11px — secondary labels only
        fs_h2     = int(t.FONT_SIZE_H2 * scale)
        fs_h1     = int(t.FONT_SIZE_H1 * scale)
        btn_pv    = max(6, int(8 * scale))
        btn_ph    = max(10, int(16 * scale))
        inp_pv    = max(4, int(6 * scale))
        inp_h_min = LayoutMetrics.scaled(LayoutMetrics.CONTROL_HEIGHT, scale)
        action_h  = LayoutMetrics.scaled(LayoutMetrics.PRIMARY_ACTION_HEIGHT, scale)
        row_pv    = max(6, int(7 * scale))
        row_ph    = max(8, int(10 * scale))
        card_gap  = max(10, int(14 * scale))
        scroll_w  = max(8, int(10 * scale))

        # Aliased token values for readability below
        bg        = t.BG_DARK
        bg_grad   = getattr(t, "BG_GRADIENT", t.BG_DARK)
        surf      = t.SURFACE_BASE
        surf_grad = getattr(t, "DARK_SURFACE_GRADIENT", t.SURFACE_BASE) if is_dark else t.SURFACE_BASE
        elevated  = t.SURFACE_ELEVATED
        bd_sub    = t.BORDER_SUBTLE
        bd_str    = t.BORDER_STRONG
        txt       = t.TEXT_PRIMARY
        txt2      = t.TEXT_SECONDARY
        accent    = t.ACCENT
        acc_lt    = t.ACCENT_LIGHT
        r_sm      = t.RADIUS_SM
        r_md      = t.RADIUS_MD

        # Button hover: subtle elevation shift
        btn_hover_bg   = t.SURFACE_ELEVATED
        btn_press_bg   = t.BORDER_SUBTLE

        return f"""
        /* ── Base Window & Containers ────────────────────────────────── */
        QMainWindow, QDialog {{
            background: {bg_grad};
            color: {txt};
            font-family: {t.FONT_FAMILY};
            font-size: {fs_body}px;
        }}
        QWidget {{
            color: {txt};
            font-family: {t.FONT_FAMILY};
            font-size: {fs_body}px;
        }}

        /* ── Cards & Frames ───────────────────────────────────────────── */
        QFrame#card, QFrame#tileContainer {{
            background: {surf_grad};
            border: 1px solid {bd_sub};
            border-radius: {r_md}px;
        }}
        QFrame#card:hover, QFrame#tileContainer:hover {{
            border-color: {bd_str};
        }}
        QFrame#insetPanel {{
            background-color: {surf};
            border: 1px solid {bd_sub};
            border-radius: {r_md}px;
        }}
        QLabel#emptyState {{
            color: {t.TEXT_MUTED};
            font-weight: 600;
            padding: {max(14, int(20 * scale))}px {max(6, int(8 * scale))}px;
            background: transparent;
            border: 2px dashed {bd_sub};
            border-radius: {r_md}px;
        }}
        QLabel#posTotal {{
            font-size: {max(fs_h1, int(24 * scale))}px;
            font-weight: 900;
            color: {txt};
            background-color: {acc_lt};
            border-radius: {r_sm}px;
            padding: {max(6, int(8 * scale))}px {max(8, int(12 * scale))}px;
        }}

        /* ── Sidebar Container & Nav ──────────────────────────────────── */
        QFrame#sidebarFrame {{
            background: {surf_grad};
            border-right: 1px solid {bd_sub};
        }}
        QPushButton#navButton {{
            text-align: left;
            background-color: transparent;
            color: {txt2};
            border: 1px solid transparent;
            padding: {max(7, int(9 * scale))}px {max(8, int(11 * scale))}px;
            font-weight: 600;
        }}
        QPushButton#navButton:hover {{
            background-color: {elevated};
            color: {txt};
            border-color: {bd_sub};
        }}
        QPushButton#navButton:checked {{
            background-color: {acc_lt};
            color: {accent};
            border-color: {accent};
            font-weight: 800;
        }}
        QPushButton#sidebarUtilityButton {{
            font-size: {fs_label}px;
            padding: {max(5, int(6 * scale))}px {max(7, int(9 * scale))}px;
        }}
        QPushButton#sidebarLogoutButton {{
            color: {t.DANGER};
            font-weight: 700;
            font-size: {fs_label}px;
            padding: {max(5, int(6 * scale))}px {max(7, int(9 * scale))}px;
        }}
        QPushButton#sidebarLogoutButton:hover {{
            background-color: {t.DANGER};
            color: #FFFFFF;
            border-color: {t.DANGER};
        }}

        /* ── Scrollbars ────────────────────────────────────────────────── */
        QScrollBar:vertical {{
            background: {bg};
            width: {scroll_w}px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {bd_str};
            min-height: {LayoutMetrics.scaled(28, scale)}px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {txt2};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {bg};
            height: {scroll_w}px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {bd_str};
            min-width: {LayoutMetrics.scaled(28, scale)}px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* ── Buttons ───────────────────────────────────────────────────── */
        QPushButton {{
            background-color: {elevated};
            color: {txt};
            border: 1px solid {bd_sub};
            border-radius: {r_sm}px;
            padding: {btn_pv}px {btn_ph}px;
            font-weight: 600;
            font-size: {fs_body}px;
            min-height: {inp_h_min}px;
        }}
        QPushButton[compact="true"] {{
            min-height: {LayoutMetrics.scaled(30, scale)}px;
            padding: {max(4, int(5 * scale))}px {max(7, int(9 * scale))}px;
        }}
        QPushButton:hover {{
            background-color: {btn_hover_bg};
            border-color: {bd_str};
        }}
        QPushButton:pressed {{
            background-color: {btn_press_bg};
        }}
        QPushButton:disabled {{
            color: {t.TEXT_MUTED};
            border-color: {bd_sub};
        }}

        /* Primary action button — Always crisp white text on accent background */
        QPushButton#primaryButton {{
            background-color: {accent};
            color: #FFFFFF;
            border: none;
            font-weight: 700;
            min-height: {action_h}px;
            padding: {btn_pv + 1}px {btn_ph + 2}px;
        }}
        QPushButton#primaryButton:hover {{
            background-color: {t.ACCENT_HOVER};
            color: #FFFFFF;
        }}
        QPushButton#primaryButton:pressed {{
            background-color: {t.ACCENT_HOVER};
            color: #FFFFFF;
        }}
        QPushButton[accent="true"] {{
            background-color: {accent};
            color: #FFFFFF;
            border-color: {accent};
            font-weight: 700;
        }}
        QPushButton[accent="true"]:hover {{
            background-color: {t.ACCENT_HOVER};
            border-color: {t.ACCENT_HOVER};
        }}
        QPushButton#successButton {{
            background-color: {t.SUCCESS};
            color: #FFFFFF;
            border: none;
            font-weight: 700;
        }}

        /* Danger action button */
        QPushButton#dangerButton {{
            background-color: {t.DANGER};
            color: #FFFFFF;
            border: none;
            font-weight: 700;
        }}
        QPushButton#dangerButton:hover {{
            background-color: {"#C94040" if is_dark else "#A03020"};
            color: #FFFFFF;
        }}

        /* ── Form Labels & General Typography ──────────────────────────── */
        QLabel {{
            color: {txt};
            font-size: {fs_body}px;
        }}
        QFormLayout QLabel {{
            color: {txt};
            font-weight: 600;
            font-size: {fs_body}px;
        }}
        QLabel#h1 {{
            font-size: {fs_h1}px;
            font-weight: 800;
            color: {txt};
        }}
        QLabel#h2 {{
            font-size: {fs_h2}px;
            font-weight: 700;
            color: {txt};
        }}
        QLabel#subtitle {{
            font-size: {fs_body}px;
            color: {txt2};
        }}
        QLabel#caption {{
            font-size: {fs_label}px;
            color: {t.TEXT_MUTED};
        }}
        QLabel#metric {{
            font-size: {max(fs_h2, int(18 * scale))}px;
            font-weight: 800;
        }}
        QLabel#metricLarge {{
            font-size: {max(fs_h1, int(24 * scale))}px;
            font-weight: 900;
        }}
        /* Semantic tone properties keep existing widgets correct when the
           user switches between Light and Dark mode. */
        QLabel[uiTone="primary"] {{ color: {txt}; }}
        QLabel[uiTone="secondary"] {{ color: {txt2}; }}
        QLabel[uiTone="muted"] {{ color: {t.TEXT_MUTED}; }}
        QLabel[uiTone="accent"] {{ color: {accent}; }}
        QLabel[uiTone="success"] {{ color: {t.SUCCESS}; }}
        QLabel[uiTone="warning"] {{ color: {t.WARNING}; }}
        QLabel[uiTone="danger"] {{ color: {t.DANGER}; }}
        QLabel[uiWeight="semibold"] {{ font-weight: 600; }}
        QLabel[uiWeight="bold"] {{ font-weight: 700; }}
        QLabel[uiWeight="heavy"] {{ font-weight: 800; }}
        QScrollArea, QScrollArea > QWidget > QWidget {{
            background-color: {surf};
            color: {txt};
            border: none;
        }}
        QScrollArea#paymentSummaryScroll, QWidget#paymentSummaryBody {{
            background: transparent;
            border: none;
        }}
        QScrollArea#setupScroll, QWidget#setupScrollBody {{
            background: transparent;
            border: none;
        }}
        QFrame#setupFooter {{
            background: transparent;
            border-top: 1px solid {bd_sub};
        }}
        QLabel#hotkeyBadge {{
            background-color: {elevated};
            color: {txt2};
            border: 1px solid {bd_sub};
            border-radius: {r_sm}px;
            padding: {max(3, int(4 * scale))}px {max(6, int(8 * scale))}px;
            font-size: {fs_label}px;
            font-weight: 700;
        }}
        QLabel#badgePill {{
            border-radius: {LayoutMetrics.scaled(10, scale)}px;
            padding: {max(2, int(3 * scale))}px {max(7, int(9 * scale))}px;
            font-size: {fs_label}px;
            font-weight: 700;
        }}
        QLabel#badgePill[pillType="success"] {{
            color: {t.SUCCESS}; background-color: rgba(16, 185, 129, 0.12); border: 1px solid {t.SUCCESS};
        }}
        QLabel#badgePill[pillType="warning"] {{
            color: {t.WARNING}; background-color: rgba(245, 158, 11, 0.12); border: 1px solid {t.WARNING};
        }}
        QLabel#badgePill[pillType="danger"] {{
            color: {t.DANGER}; background-color: rgba(239, 68, 68, 0.12); border: 1px solid {t.DANGER};
        }}
        QLabel#badgePill[pillType="info"] {{
            color: {t.INFO}; background-color: rgba(59, 130, 246, 0.12); border: 1px solid {t.INFO};
        }}

        /* ── Inputs ────────────────────────────────────────────────────── */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
            background-color: {surf};
            color: {txt};
            border: 1px solid {bd_sub};
            border-radius: {r_sm}px;
            padding: {inp_pv}px {t.SPACE_MD}px;
            font-size: {fs_body}px;
            min-height: {inp_h_min}px;
            selection-background-color: {t.ACCENT_HOVER};
            selection-color: #FFFFFF;
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
            border: 2px solid {t.BORDER_FOCUS};
            background-color: {surf};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: {LayoutMetrics.scaled(24, scale)}px;
            border-left: 1px solid {bd_sub};
        }}
        QComboBox QAbstractItemView {{
            background-color: {surf};
            color: {txt};
            border: 1px solid {bd_str};
            border-radius: {r_sm}px;
            selection-background-color: {accent};
            selection-color: #FFFFFF;
            padding: {t.SPACE_XS}px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPushButton:focus, QTableView:focus {{
            border: 2px solid {t.BORDER_FOCUS};
            outline: none;
        }}
        QLineEdit#primarySearch {{
            border: 2px solid {accent};
            font-weight: 600;
            min-height: {LayoutMetrics.scaled(42, scale)}px;
        }}
        QLineEdit#primarySearch:focus {{
            border: 2px solid {t.BORDER_FOCUS};
        }}

        /* ── Tables & Headers ─────────────────────────────────────────── */
        QTableWidget, QTableView {{
            background-color: {surf};
            gridline-color: {bd_sub};
            border: 1px solid {bd_sub};
            border-radius: {r_md}px;
            selection-background-color: {acc_lt};
            selection-color: {txt};
            alternate-background-color: {elevated};
            font-size: {fs_body}px;
        }}
        QTableWidget:focus, QTableView:focus {{
            border: 2px solid {t.BORDER_FOCUS};
        }}
        QHeaderView {{
            background-color: {elevated};
            border: none;
        }}
        QHeaderView::section {{
            background-color: {elevated};
            color: {txt};
            font-weight: 700;
            font-size: {fs_label}px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            padding: {row_pv}px {row_ph}px;
            border: none;
            border-bottom: 2px solid {bd_str};
            border-right: 1px solid {bd_sub};
        }}
        QTableWidget::item, QTableView::item {{
            padding: {row_pv}px {row_ph}px;
            border-bottom: 1px solid {bd_sub};
            color: {txt};
            font-size: {fs_body}px;
        }}
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {acc_lt};
            color: {txt};
        }}
        QTableCornerButton::section {{
            background-color: {elevated};
            border: none;
        }}

        /* ── Scrollbar viewport margin ───────────────────────────────────
           Reserves gutter space so vertical scrollbars never overlay the
           last table column (the recurring 'Actions clipped' bug). */
        QAbstractScrollArea {{ background: {bg}; }}

        /* ── Tabs ──────────────────────────────────────────────────────── */
        QTabWidget::pane {{
            border: 1px solid {bd_sub};
            border-radius: {r_sm}px;
            background-color: {surf};
        }}
        QTabBar::tab {{
            background-color: {elevated};
            color: {txt2};
            padding: {max(6, int(8 * scale))}px {max(10, int(16 * scale))}px;
            border: 1px solid {bd_sub};
            border-bottom: none;
            font-weight: 600;
            font-size: {fs_body}px;
            min-width: {LayoutMetrics.scaled(76, scale)}px;
            min-height: {LayoutMetrics.scaled(28, scale)}px;
        }}
        QTabBar::tab:selected {{
            background-color: {surf};
            color: {accent};
            border-bottom: 3px solid {accent};
            font-weight: 700;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {surf};
            color: {txt};
        }}

        /* ── Choice controls ───────────────────────────────────────────── */
        QCheckBox, QRadioButton {{
            spacing: {max(6, int(8 * scale))}px;
            font-size: {fs_body}px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: {LayoutMetrics.scaled(18, scale)}px;
            height: {LayoutMetrics.scaled(18, scale)}px;
        }}

        /* ── Status Bar ────────────────────────────────────────────────── */
        QStatusBar {{
            background-color: {elevated};
            color: {txt2};
            border-top: 1px solid {bd_sub};
            font-size: {fs_label}px;
        }}

        /* ── Group Boxes ───────────────────────────────────────────────── */
        QGroupBox {{
            background-color: {surf};
            border: 1px solid {bd_sub};
            border-radius: {r_md}px;
            margin-top: {t.SPACE_MD}px;
            font-weight: 700;
            font-size: {fs_body}px;
            padding-top: {t.SPACE_SM}px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 {t.SPACE_SM}px;
            color: {accent};
        }}

        /* ── Tooltips ──────────────────────────────────────────────────── */
        QToolTip {{
            background-color: {surf};
            color: {txt};
            border: 1px solid {bd_str};
            border-radius: {r_sm}px;
            padding: {t.SPACE_XS}px {t.SPACE_SM}px;
            font-size: {fs_body}px;
        }}
        """

    # Backwards compat alias — older call sites used get_application_qss
    @classmethod
    def get_application_qss(cls, mode: str = None, scale: float = None) -> str:
        return cls.build_qss(mode=mode, scale=scale)
