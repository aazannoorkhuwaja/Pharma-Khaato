"""Small helpers for theme-safe semantic UI styling.

Widgets store semantic intent (accent, warning, muted, etc.) as properties while
ThemeManager owns the actual palette. This prevents light/dark switching from
leaving stale inline colors on already-created screens.
"""


def set_tone(widget, tone: str, weight: str | None = None):
    widget.setProperty("uiTone", tone)
    if weight is not None:
        widget.setProperty("uiWeight", weight)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()
    return widget
