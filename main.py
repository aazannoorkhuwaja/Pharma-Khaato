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
    parser.add_argument("--configure-network", action="store_true", help="Choose this computer's shop/counter connection")
    parser.add_argument("--shop-server", action="store_true", help="Start the shop's shared-counter service")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Verify writable storage, SQLite integrity/schema and runtime readiness, then exit",
    )
    parser.add_argument("--functional-smoke", action="store_true", help="Verify an isolated disposable shop and major screens, then exit")
    parser.add_argument("--smoke-report", help="Write a machine-readable functional-check result")
    args = parser.parse_args()
    if args.smoke_report and not args.functional_smoke:
        parser.error("--smoke-report requires --functional-smoke")

    if args.headless:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    elif args.platform:
        os.environ["QT_QPA_PLATFORM"] = args.platform

    if args.shop_server:
        from scripts.run_shop_server import main as run_server
        sys.argv = [sys.argv[0]]
        return run_server()

    check_gui()

    if args.functional_smoke:
        from core.installed_smoke import run
        from core.installed_smoke import _progress
        import json
        import traceback
        from pathlib import Path
        from config import ApplicationSettings
        report = {"ok": False, "version": ApplicationSettings.APP_VERSION, "check": "functional-smoke"}
        try:
            result = run()
            report["ok"] = result == 0
            _progress('finished')
        except Exception as exc:
            # A windowed Windows EXE must not open a traceback dialog in CI.
            report.update(error=str(exc), traceback=traceback.format_exc())
            logger.exception("Installed functional check failed")
            result = 2
        if args.smoke_report:
            Path(args.smoke_report).write_text(json.dumps(report), encoding="utf-8")
        return result

    if args.configure_network:
        from PySide6.QtWidgets import QApplication
        from ui.dialogs.counter_connection_dialog import configure_shop_connection
        app = QApplication.instance() or QApplication([sys.argv[0]])
        if not configure_shop_connection():
            return 0

    if args.self_check:
        raise SystemExit(run_self_check())

    try:
        sys.exit(launch_desktop() or 0)
    except Exception as e:
        logger.exception("Fatal application startup/runtime error: %s", e)
        print(f"Application error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    raise SystemExit(main() or 0)
