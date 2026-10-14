"""
Pharma-Khaato Native PySide6 Toast Widget
Non-blocking, auto-dismissing transient toast notification for status feedback.

Supports four semantic types: SUCCESS, INFO, WARNING, ERROR — each mapped to the
design-system's colour tokens so feedback carries meaning, not just red/green.

Optional undo_callback: when provided, an "Undo" button is rendered inline.
Clicking it cancels the auto-dismiss, hides the toast, and fires the callback.
"""

import copy
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
from ui.theme.tokens import ThemeTokens


class ToastType:
    """Semantic toast types. Pick the one that matches the nature of the event."""
    SUCCESS = "success"   # Positive completion — sale confirmed, item added, hold saved
    INFO    = "info"      # Neutral status — item recalled, search hint
    WARNING = "warning"   # Recoverable problem — empty cart action, session not open
    ERROR   = "error"     # Hard failure — transaction failed, network error, bad input


class Toast(QFrame):
    """
    Transient banner notification for success, error, warning, and informational feedback.
    Replaces blocking QMessageBox modals for high-frequency counter operation.
    Fluid Apple-style spring animation: slides & fades smoothly.
    """

    # Expose type constants directly on the class for convenience
    SUCCESS = ToastType.SUCCESS
    INFO    = ToastType.INFO
    WARNING = ToastType.WARNING
    ERROR   = ToastType.ERROR

    # Colour mapping: (border_accent, background) per type
    _COLORS = {
        ToastType.SUCCESS: (ThemeTokens.SUCCESS,  "rgba(16, 185, 129, 0.94)"),
        ToastType.INFO:    (ThemeTokens.INFO,      "rgba(2, 132, 199, 0.94)"),
        ToastType.WARNING: (ThemeTokens.WARNING,   "rgba(217, 119, 6, 0.94)"),
        ToastType.ERROR:   (ThemeTokens.DANGER,    "rgba(220, 38, 38, 0.94)"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss_smoothly)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim_group = None

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(18, 10, 18, 10)
        self._layout.setSpacing(12)

        self.lbl_msg = QLabel()
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._layout.addWidget(self.lbl_msg, 1)

        # Undo button — hidden by default, shown only when undo_callback is set
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setCursor(Qt.PointingHandCursor)
        self.btn_undo.setProperty("compact", True)
        self.btn_undo.setMinimumHeight(30)
        self.btn_undo.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.25);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.5);
                border-radius: 4px;
                padding: 0 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.40);
            }
        """)
        self.btn_undo.hide()
        self._layout.addWidget(self.btn_undo)

        self.hide()

    def show_message(
        self,
        text: str,
        toast_type: str = ToastType.SUCCESS,
        duration_ms: int = 2000,
        undo_callback=None,
        is_error: bool = False,
    ):
        """
        Display the toast banner with fluid entry motion.
        """
        if not isinstance(self, Toast):
            # Classmethod fallback call site handling
            parent = self
            return show_toast(parent, text, toast_type=toast_type, duration_ms=duration_ms, undo_callback=undo_callback, is_error=is_error)

        if is_error:
            toast_type = ToastType.ERROR

        self._dismiss_timer.stop()
        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        if getattr(self, '_undo_connection', None) is not None:
            try:
                self.btn_undo.clicked.disconnect(self._undo_connection)
            except (RuntimeError, Exception):
                pass
            self._undo_connection = None

        _, bg = self._COLORS.get(toast_type, self._COLORS[ToastType.SUCCESS])

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: {ThemeTokens.RADIUS_SM}px;
                font-weight: 700;
            }}
            QLabel {{
                color: #FFFFFF;
            }}
        """)

        self.lbl_msg.setText(text)
        if self.parentWidget() is not None:
            available = max(260, self.parentWidget().width() - 64)
            self.lbl_msg.setMaximumWidth(min(560, available))

        if undo_callback is not None:
            self.btn_undo.show()
            cb = lambda: self._on_undo(undo_callback)
            self.btn_undo.clicked.connect(cb)
            self._undo_connection = cb
        else:
            self.btn_undo.hide()

        self.adjustSize()
        pw = self.parentWidget().width() if self.parentWidget() else 800
        target_x = (pw - self.width()) // 2
        target_y = 16

        # Set initial off-screen state & zero opacity
        self.move(target_x, 0)
        self._opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        # Build Apple-style spring slide & fade in animation
        anim_pos = QPropertyAnimation(self, b"pos", self)
        anim_pos.setStartValue(QPoint(target_x, 0))
        anim_pos.setEndValue(QPoint(target_x, target_y))
        anim_pos.setDuration(180)
        anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        anim_fade = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)
        anim_fade.setDuration(180)
        anim_fade.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(anim_pos)
        self._anim_group.addAnimation(anim_fade)
        self._anim_group.start(QParallelAnimationGroup.KeepWhenStopped)

        self._dismiss_timer.start(duration_ms)

    def dismiss_smoothly(self):
        """Exit animation: slide up and fade out before hiding."""
        self._dismiss_timer.stop()
        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        pw = self.parentWidget().width() if self.parentWidget() else 800
        curr_x = self.x()

        anim_pos = QPropertyAnimation(self, b"pos", self)
        anim_pos.setStartValue(self.pos())
        anim_pos.setEndValue(QPoint(curr_x, 0))
        anim_pos.setDuration(140)
        anim_pos.setEasingCurve(QEasingCurve.InCubic)

        anim_fade = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim_fade.setStartValue(self._opacity_effect.opacity())
        anim_fade.setEndValue(0.0)
        anim_fade.setDuration(140)
        anim_fade.setEasingCurve(QEasingCurve.InCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(anim_pos)
        self._anim_group.addAnimation(anim_fade)
        self._anim_group.finished.connect(self.hide)
        self._anim_group.start(QParallelAnimationGroup.KeepWhenStopped)

    def _on_undo(self, callback):
        """Cancel the dismiss timer, hide the toast smoothly, then fire the undo callback."""
        self._dismiss_timer.stop()
        self.dismiss_smoothly()
        callback()


def show_toast(
    parent,
    text: str,
    toast_type: str = ToastType.SUCCESS,
    duration_ms: int = 2000,
    undo_callback=None,
    is_error: bool = False,
):
    """
    Module-level helper that safely finds or attaches a single Toast host widget to a parent/dialog.
    """
    if parent is None:
        return
    t = getattr(parent, "_active_toast_host", None)
    if t is None or not isinstance(t, Toast):
        t = Toast(parent)
        parent._active_toast_host = t
    t.show_message(text, toast_type=toast_type, duration_ms=duration_ms, undo_callback=undo_callback, is_error=is_error)


