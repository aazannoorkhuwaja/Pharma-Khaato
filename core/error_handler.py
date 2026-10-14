"""Process-wide exception logging for GUI and CLI execution."""

from __future__ import annotations

import sys
import traceback

from core.logger import get_logger

logger = get_logger("PharmaKhaatoCrash")


def install_global_exception_hook() -> None:
    """Log uncaught exceptions while preserving normal interpreter semantics."""
    previous_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, exc_value, exc_tb)
            return
        formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical("Uncaught application exception:\n%s", formatted)
        previous_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
