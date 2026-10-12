"""Pharma-Khaato screen router with cache-aware navigation.

Screens stay alive in a QStackedWidget. Secondary screens are created lazily,
and data-heavy ``on_screen_show`` refreshes run only when a relevant business
domain changed or a conservative max-age expires.
"""

from __future__ import annotations

from time import perf_counter
from typing import Callable, Iterable

from PySide6.QtWidgets import QStackedWidget, QWidget

from core.data_revision import snapshot
from core.logger import get_logger

logger = get_logger("PharmaKhaatoRouter")


class AppRouter(QStackedWidget):
    """Fast screen switching without unnecessary database/table rebuilds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._screens: dict[str, QWidget] = {}
        self._factories: dict[str, Callable[[], QWidget]] = {}
        self._factory_constructor_loads_data: dict[str, bool] = {}
        self._screen_domains: dict[str, tuple[str, ...]] = {}
        self._screen_max_age: dict[str, float] = {}
        self._rendered_revisions: dict[str, tuple[tuple[str, int], ...]] = {}
        self._last_refresh_at: dict[str, float] = {}
        self._current_key: str | None = None

    @staticmethod
    def _clean_domains(domains: Iterable[str] | None) -> tuple[str, ...]:
        return tuple(sorted({str(item).strip().lower() for item in (domains or ()) if str(item).strip()}))

    def register_screen(
        self,
        name: str,
        widget: QWidget,
        *,
        domains: Iterable[str] | None = None,
        max_age_seconds: float = 30.0,
        data_is_current: bool = False,
    ):
        """Register a persistent view and its data dependencies."""
        self._screens[name] = widget
        self._screen_domains[name] = self._clean_domains(domains)
        self._screen_max_age[name] = max(0.0, float(max_age_seconds))
        self.addWidget(widget)
        if self._current_key is None:
            self._current_key = name
        if data_is_current:
            self.mark_screen_current(name)

    def register_screen_factory(
        self,
        name: str,
        factory_fn: Callable[[], QWidget],
        *,
        domains: Iterable[str] | None = None,
        max_age_seconds: float = 30.0,
        constructor_loads_data: bool = True,
    ):
        """Register a lazily created screen plus cache invalidation metadata."""
        self._factories[name] = factory_fn
        self._screen_domains[name] = self._clean_domains(domains)
        self._screen_max_age[name] = max(0.0, float(max_age_seconds))
        self._factory_constructor_loads_data[name] = bool(constructor_loads_data)

    def mark_screen_current(self, name: str) -> None:
        """Record that a screen currently reflects its declared data domains."""
        domains = self._screen_domains.get(name, ())
        self._rendered_revisions[name] = snapshot(domains)
        self._last_refresh_at[name] = perf_counter()

    def mark_current_screen_current(self) -> None:
        if self._current_key in self._screens:
            self.mark_screen_current(self._current_key)

    def invalidate_screen(self, name: str) -> None:
        """Force the named screen to refresh on its next visit."""
        self._rendered_revisions.pop(name, None)
        self._last_refresh_at.pop(name, None)

    def _needs_refresh(self, name: str) -> bool:
        if name not in self._rendered_revisions:
            return True

        domains = self._screen_domains.get(name, ())
        if snapshot(domains) != self._rendered_revisions.get(name):
            return True

        max_age = self._screen_max_age.get(name, 30.0)
        if max_age > 0:
            last = self._last_refresh_at.get(name, 0.0)
            if perf_counter() - last >= max_age:
                return True
        return False

    def navigate_to(self, name: str, animate: bool = True) -> bool:
        """Switch screens immediately and refresh only when data can be stale."""
        if name == self._current_key and name in self._screens:
            # Clicking the already-active feature must be effectively free.
            return True

        # A screen generally refreshes itself after its own successful mutation.
        # Recording the latest revisions as we leave avoids repeating that same
        # work when the user comes back a moment later.
        if self._current_key in self._screens:
            self.mark_screen_current(self._current_key)

        started = perf_counter()
        created = False
        if name not in self._screens:
            factory = self._factories.get(name)
            if factory is None:
                return False
            widget = factory()
            created = True
            self.register_screen(
                name,
                widget,
                domains=self._screen_domains.get(name, ()),
                max_age_seconds=self._screen_max_age.get(name, 30.0),
                data_is_current=self._factory_constructor_loads_data.get(name, True),
            )

        target = self._screens[name]
        self.setCurrentWidget(target)
        self._current_key = name

        # Factory-created screens in the current codebase already populate their
        # initial data in __init__. Do not immediately execute the exact same
        # queries again. Subsequent visits use revision-aware refreshes.
        if not created and self._needs_refresh(name) and hasattr(target, "on_screen_show"):
            refresh_started = perf_counter()
            target.on_screen_show()
            self.mark_screen_current(name)
            refresh_ms = (perf_counter() - refresh_started) * 1000.0
            if refresh_ms >= 120.0:
                logger.info("Slow screen refresh: %s took %.1f ms", name, refresh_ms)
        elif created and name not in self._rendered_revisions:
            # Future factories may opt out of constructor loading.
            if hasattr(target, "on_screen_show"):
                target.on_screen_show()
            self.mark_screen_current(name)

        nav_ms = (perf_counter() - started) * 1000.0
        if nav_ms >= 120.0:
            logger.info("Slow navigation: %s took %.1f ms%s", name, nav_ms, " (first load)" if created else "")
        return True

    def get_current_key(self) -> str | None:
        return self._current_key

    def get_screen(self, name: str) -> QWidget | None:
        return self._screens.get(name)
