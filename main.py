"""
Pharma-Khaato — Production Application Entry Point
Launches the native desktop application shell with PySide6 and support for
headless diagnostics used by release/demo smoke tests.
"""

import os
import sys
import argparse

from core.error_handler import install_global_exception_hook
from core.logger import get_logger

logger = get_logger("PharmaKhaatoMain")


def check_gui():
    """Verify PySide6 GUI environment dependencies."""
    try:
        import PySide6  # noqa: F401
    except ImportError:
        print("ERROR: PySide6 is required for Pharma-Khaato Desktop application.")
        sys.exit(1)


def launch_desktop():
    from ui.app.application import run_app
    return run_app()


def run_self_check() -> int:
    """Run a non-interactive installed-build health check and exit."""
    try:
        from core.readiness_service import run_readiness_checks, format_readiness_report

        report = run_readiness_checks()
        print(format_readiness_report(report))
        return 0 if report.get("ok") else 2
    except Exception as exc:
        logger.exception("Launch self-check failed unexpectedly: %s", exc)
        print(f"[FAIL] Launch self-check crashed: {exc}", file=sys.stderr)
        return 2


def main():
    install_global_exception_hook()
    parser = argparse.ArgumentParser(description="Pharma-Khaato POS & Pharmacy Management System")
    parser.add_argument("--headless", action="store_true", help="Run Qt application in offscreen headless mode")
    parser.add_argument("--platform", type=str, default=None, help="Specify Qt QPA platform plugin (e.g. xcb, wayland, offscreen)")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Verify writable storage, SQLite integrity/schema and runtime readiness, then exit",
    )
    args = parser.parse_args()

    if args.headless:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    elif args.platform:
        os.environ["QT_QPA_PLATFORM"] = args.platform

    check_gui()

    if args.self_check:
        raise SystemExit(run_self_check())

    try:
        sys.exit(launch_desktop() or 0)
    except Exception as e:
        logger.exception("Fatal application startup/runtime error: %s", e)
        print(f"Application error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
