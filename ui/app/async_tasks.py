"""Small reusable worker pool for non-blocking desktop operations.

Database reads, report generation, backups, exports and other potentially slow
operations must not block Qt's GUI thread. ``AsyncTaskRunner`` executes plain
Python callables on ``QThreadPool.globalInstance()`` and marshals results back to
Qt safely through signals.

``run_latest`` is intentionally included for search/report style work: if the
user changes a date or starts another request before an older one finishes, only
the newest result for that key is delivered to the UI.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _TaskSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class _FunctionTask(QRunnable):
    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self.fn = fn
        self.signals = _TaskSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            value = self.fn()
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        else:
            self.signals.result.emit(value)
        finally:
            self.signals.finished.emit()


class AsyncTaskRunner(QObject):
    """Run callables away from the GUI thread and deliver results safely."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._active: dict[int, _FunctionTask] = {}
        self._versions: dict[str, int] = {}

    def _track(self, task: _FunctionTask) -> None:
        token = id(task)
        self._active[token] = task
        # Capture only the integer token, not the task itself. This avoids a
        # Python reference cycle while still keeping the QRunnable alive until
        # Qt reports that it finished.
        task.signals.finished.connect(lambda token=token: self._active.pop(token, None))

    def run(
        self,
        fn: Callable[[], Any],
        on_result: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        task = _FunctionTask(fn)
        self._track(task)
        task.signals.result.connect(on_result)
        if on_error is not None:
            task.signals.error.connect(on_error)
        self._pool.start(task)

    def run_latest(
        self,
        key: str,
        fn: Callable[[], Any],
        on_result: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Deliver only the newest result submitted for ``key``."""
        version = self._versions.get(key, 0) + 1
        self._versions[key] = version

        def accept_result(value):
            if self._versions.get(key) == version:
                on_result(value)

        def accept_error(message: str):
            if self._versions.get(key) == version and on_error is not None:
                on_error(message)

        self.run(fn, accept_result, accept_error if on_error is not None else None)

    def invalidate(self, key: str) -> None:
        """Make any in-flight result for ``key`` stale without cancelling work."""
        self._versions[key] = self._versions.get(key, 0) + 1
