"""Responsive desktop layout metrics for Pharma-Khaato.

Qt desktop applications do not use CSS media queries, so the project keeps its
breakpoints and ergonomic sizing rules here.  Screens may use these constants
without inventing one-off widths or touch targets.
"""


class LayoutMetrics:
    # Main shell breakpoints.  Widths are in logical Qt pixels (DPI independent).
    # A 1366x768 physical Windows monitor at 150% scaling is only about
    # 910x512 Qt logical pixels, often ~480 high after the taskbar. The
    # previous 900x600 minimum could extend checkout beyond the desktop.
    SHELL_MIN_WIDTH = 820
    SHELL_MIN_HEIGHT = 440
    SIDEBAR_FULL_AT = 1260
    SIDEBAR_COMPACT_AT = 1080

    SIDEBAR_FULL = 230
    SIDEBAR_COMPACT = 176
    SIDEBAR_MINI = 84

    CONTENT_MARGIN = 16
    CONTENT_GAP = 14

    # Controls are sized for mouse + touch-screen pharmacy counters.
    CONTROL_HEIGHT = 38
    PRIMARY_ACTION_HEIGHT = 44
    TABLE_ROW_HEIGHT = 38
    # Rows containing an embedded action control need extra vertical breathing
    # room because a styled QPushButton's content + padding + border is taller
    # than an ordinary text row. Keeping this explicit prevents clipped/stacked
    # buttons at 100%, 125%, and 150% accessibility scales.
    TABLE_ACTION_ROW_HEIGHT = 52

    # Flexible side panels. Never hard-lock a business panel to one pixel width.
    SIDE_PANEL_MIN = 288
    SIDE_PANEL_IDEAL = 340
    SIDE_PANEL_MAX = 430

    # Dialogs remain usable on 1366x768 laptops and high-DPI screens.
    DIALOG_MARGIN = 48

    @classmethod
    def startup_window_size(cls, available_width: int, available_height: int) -> tuple[int, int]:
        """Choose a sensible Qt-logical size without exceeding the usable screen.

        Screen geometry already accounts for operating-system DPI scaling.
        Do not divide by the scale factor a second time. Small monitors must
        stay reachable even if preferred size exceeds the desktop.
        """
        width = max(1, int(available_width))
        height = max(1, int(available_height))
        return (
            min(width, max(cls.SHELL_MIN_WIDTH, int(width * 0.94)), 1440),
            min(height, max(cls.SHELL_MIN_HEIGHT, int(height * 0.90)), 900),
        )

    @staticmethod
    def scaled(value: int, scale: float) -> int:
        return max(1, int(round(value * scale)))
