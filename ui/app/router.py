"""
Pharma-Khaato Screen Router
Manages QStackedWidget transitions between application screens.
Hard-cut only — no animation wrapper. This is correct for business desktop software
and removes an entire class of Qt/non-top-level-window opacity bugs.
"""

from PySide6.QtWidgets import QStackedWidget, QWidget


class AppRouter(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._screens: dict[str, QWidget] = {}
        self._factories: dict[str, callable] = {}
        self._current_key: str | None = None

    def register_screen(self, name: str, widget: QWidget):
        """Registers a view widget under a unique screen name."""
        self._screens[name] = widget
        self.addWidget(widget)
        if self._current_key is None:
            self._current_key = name

    def register_screen_factory(self, name: str, factory_fn):
        """Registers a screen creation factory function for lazy instantiation."""
        self._factories[name] = factory_fn

    def navigate_to(self, name: str, animate: bool = True) -> bool:
        """
        Switches to the named screen, instantiating it lazily if registered as a factory.
        """
        if name not in self._screens:
            if name in self._factories:
                widget = self._factories[name]()
                self.register_screen(name, widget)
            else:
                return False

        target = self._screens[name]
        self.setCurrentWidget(target)
        self._current_key = name

        if hasattr(target, "on_screen_show"):
            target.on_screen_show()

        return True

    def get_current_key(self) -> str:
        return self._current_key

    def get_screen(self, name: str) -> QWidget:
        return self._screens.get(name)
