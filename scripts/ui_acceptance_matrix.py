#!/usr/bin/env python3
"""Isolated cross-platform UI acceptance evidence for Pharma-Khaato.

This is a *simulated*, offscreen Qt acceptance matrix, not a physical display,
scanner, printer, or live-shop certification. Always uses scripts.demo_mode's
guarded .demo-data directory; never connects to a customer's database.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from scripts.demo_mode import reset_demo_storage, seed_demo_database
from PySide6.QtCore import QPoint, QRect, Qt, QThreadPool
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from ui.app.main_window import MainWindow
from ui.app.state.session_state import SessionState
from ui.theme.theme_manager import ThemeManager
from ui.screens.pos_screen import POSScreen
from ui.screens.inventory_screen import InventoryScreen
from ui.screens.customer_screen import CustomerScreen
from ui.screens.khatoo_screen import KhatooScreen
from ui.screens.cash_session_screen import CashSessionScreen
from ui.screens.reports_screen import ReportsScreen
from ui.screens.returns_screen import ReturnsScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.login_screen import LoginDialog
from ui.screens.first_run_wizard import FirstRunWizardDialog


def capture(app, widget, output):
    app.processEvents()
    QTest.qWait(75)
    app.processEvents()
    output.parent.mkdir(parents=True, exist_ok=True)
    image = widget.grab()
    if image.isNull() or not image.save(str(output), "PNG"):
        raise AssertionError(f"Could not save image: {output}")
    return {"logical_width": widget.width(), "logical_height": widget.height(),
            "pixel_width": image.width(), "pixel_height": image.height(),
            "device_pixel_ratio": round(image.devicePixelRatio(), 3)}


def wait_for_refresh(app, screen):
    runner = getattr(screen, "_tasks", None)
    for _ in range(50):
        app.processEvents()
        if runner is None or not getattr(runner, "_active", None):
            break
        QTest.qWait(40)
    app.processEvents()


def inside_window(window, widget):
    if not widget.isVisible() or widget.width() < 1 or widget.height() < 1:
        return False
    pos = widget.mapTo(window, QPoint(0, 0))
    rect = QRect(pos, widget.size())
    return window.rect().contains(rect)


def contact_sheet(images, title, output):
    """Qt-only preview index; no Pillow or external renderer dependency."""
    w, h = 420, 255
    columns = 4
    rows = (len(images) + columns - 1) // columns
    canvas = QImage(columns * w, (rows + 1) * h, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#EFF3F8"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setPen(QColor("#13273E"))
    font = QFont("Segoe UI", 13)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(16, 38, title)
    for idx, (name, filename) in enumerate(images):
        x = (idx % columns) * w + 8
        y = (idx // columns + 1) * h + 6
        image = QPixmap(str(filename))
        if image.isNull():
            continue
        scaled = image.scaled(w - 16, h - 37, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(x, y + 19, scaled)
        painter.drawText(x + 4, y + 15, name.replace("_", " ").title())
    painter.end()
    if not canvas.save(str(output), "PNG"):
        raise AssertionError(f"Could not save contact sheet {output}")


def collect():
    parser = argparse.ArgumentParser(description="Generate isolated, offscreen UI acceptance evidence")
    parser.add_argument("--output", default="artifacts/ui_acceptance", help="Relative output directory")
    parser.add_argument("--strict", action="store_true", help="Fail on critical visibility errors")
    parser.add_argument("--quick", action="store_true", help="Baseline only; suitable for quick local checks")
    args = parser.parse_args()

    result_dir = (ROOT / args.output).resolve()
    if not result_dir.is_relative_to(ROOT / "artifacts"):
        parser.error("Output directory must be inside repository artifacts/")
    result_dir.mkdir(parents=True, exist_ok=True)

    reset_demo_storage()
    summary = seed_demo_database()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    ThemeManager.load_preferences()

    state = SessionState.get_instance()
    state.set_user({"id": summary["admin_id"], "username": "admin",
                    "occupation": "Admin", "first_name": "Ahsan", "last_name": "Malik"})
    window = MainWindow()

    screens = {
        "pos": POSScreen(show_message_box=False),
        "inventory": InventoryScreen(show_message_box=False),
        "customers": CustomerScreen(show_message_box=False),
        "khatoo": KhatooScreen(show_message_box=False),
        "cash_session": CashSessionScreen(show_message_box=False),
        "reports": ReportsScreen(show_message_box=False),
        "returns": ReturnsScreen(show_message_box=False),
        "settings": SettingsScreen(show_message_box=False),
    }
    domains = {
        "pos": ("cash",),
        "inventory": ("inventory",),
        "customers": ("customers", "credit"),
        "khatoo": ("credit", "customers"),
        "cash_session": ("cash", "sales", "credit", "returns"),
        "reports": ("reports", "sales", "inventory", "credit", "returns"),
        "returns": ("returns", "sales"),
        "settings": ("settings", "staff", "backups"),
    }
    for key, screen in screens.items():
        window.router.register_screen(key, screen, domains=domains[key])
    window.set_active_user(state.current_user)
    window.show()

    scenarios = [
        ("counter_1366", 1366, 768, "light", "standard", 1.0),
        ("counter_1024", 1024, 768, "light", "standard", 1.0),
        ("minimum_900", 900, 600, "light", "compact", 1.0),
        # Emulate the Qt-logical available desktop on a physical 1366x768
        # workstation at 150% scaling. This is not a substitute for real DPI.
        ("scaled_laptop_150_available", 910, 480, "light", "compact", 1.0),
        ("scaled_laptop_150_startup", 855, 440, "light", "compact", 1.0),
        ("desktop_1920", 1920, 1080, "light", "standard", 1.0),
        ("dark_1366", 1366, 768, "dark", "standard", 1.0),
        ("compact_1366", 1366, 768, "light", "compact", 1.0),
        ("text_125", 1366, 768, "light", "standard", 1.25),
        ("text_150", 1366, 768, "light", "standard", 1.5),
    ]
    if args.quick:
        scenarios = scenarios[:1]
    checks = []
    failures = []
    warnings = []

    try:
        # Login and first-run are shown as UI-only previews, never submitted.
        ThemeManager.set_theme("light", save=False)
        ThemeManager.set_density("standard", save=False)
        ThemeManager.set_font_scale(1.0, save=False)
        app.setStyleSheet(ThemeManager.build_qss("light", 1.0))
        login = LoginDialog()
        wizard = FirstRunWizardDialog(show_message_box=False)
        for label, modal in (("login", login), ("first_run", wizard)):
            modal.show()
            app.processEvents()
            capture(app, modal, result_dir / f"{label}.png")
            modal.hide()
            modal.deleteLater()

        for label, width, height, theme, density, font_scale in scenarios:
            ThemeManager.set_theme(theme, save=False)
            ThemeManager.set_density(density, save=False)
            ThemeManager.set_font_scale(font_scale, save=False)
            # Offscreen ThemeManager.apply_theme deliberately skips native QSS
            # reapplication. Apply it explicitly for truthful themed captures.
            app.setStyleSheet(ThemeManager.build_qss(theme, font_scale))
            window.resize(width, height)
            app.processEvents()
            screenshots = []

            for key, screen in screens.items():
                window.on_nav_clicked(key)
                wait_for_refresh(app, screen)
                filename = result_dir / label / f"{key}.png"
                photo = capture(app, window, filename)
                screenshots.append((key, filename))
                visible_title = inside_window(window, window.lbl_workspace_title)
                record = {
                    "scenario": label, "screen": key,
                    "theme": theme, "density": density, "font_scale": font_scale,
                    "requested_logical_size": [width, height],
                    "rendered_logical_size": [window.width(), window.height()],
                    "image": str(filename.relative_to(result_dir)),
                    "title_visible": visible_title,
                    "screenshot": photo,
                }
                if window.width() > width + 2 or window.height() > height + 2:
                    failures.append(
                        f"{label}/{key}: forced window exceeds target desktop "
                        f"({window.width()}x{window.height()} > {width}x{height})"
                    )
                if not visible_title:
                    failures.append(f"{label}/{key}: workspace heading outside window")
                # Navigation remains readable, not merely inside a clipped
                # Qt widget. This checks text width; separately inspect captures.
                nav_clipped = [
                    name for name, button in window.nav_buttons.items()
                    if button.isVisible() and button.fontMetrics().horizontalAdvance(
                        button.text().replace("&&", "&")
                    ) > button.width() - 12
                ]
                if nav_clipped:
                    failures.append(f"{label}/{key}: sidebar nav label clipped: {nav_clipped}")
                if key == "pos":
                    pos = screens["pos"]
                    anchors = {
                        "medicine_search": pos.txt_search,
                        "sale_total": pos.lbl_total,
                        "complete_sale": pos.btn_checkout,
                    }
                    record["cashier_anchors"] = {
                        name: inside_window(window, widget)
                        for name, widget in anchors.items()
                    }
                    # Prevent false greens where anchors fit but captions or
                    # tender tiles are horizontally cut off inside a scroll panel.
                    scroll = pos.findChild(
                        __import__("PySide6.QtWidgets", fromlist=["QScrollArea"]).QScrollArea,
                        "paymentSummaryScroll",
                    )
                    viewport = scroll.viewport()
                    record["payment_tiles_fit"] = all(
                        (button.mapTo(viewport, QPoint(0, 0)).x() >= 0 and
                         button.mapTo(viewport, QPoint(0, 0)).x() + button.width() <= viewport.width())
                        for button in pos.payment_choice_buttons
                    )
                    if not record["payment_tiles_fit"]:
                        failures.append(f"{label}/pos: payment buttons horizontally clipped")
                    record["shortcuts_fit"] = (
                        pos.lbl_shortcuts.fontMetrics().horizontalAdvance(
                            pos.lbl_shortcuts.text()
                        ) <= pos.lbl_shortcuts.width() + 3
                    )
                    if not record["shortcuts_fit"]:
                        failures.append(f"{label}/pos: shortcut legend clipped")
                    record["tender_count"] = len(pos.payment_choice_buttons)
                    record["selected_tenders"] = sum(button.isChecked()
                                                     for button in pos.payment_choice_buttons)
                    for name, okay in record["cashier_anchors"].items():
                        if not okay:
                            failures.append(f"{label}/pos: {name} not fully inside window")
                    if record["tender_count"] != 5 or record["selected_tenders"] != 1:
                        failures.append(f"{label}/pos: payment tiles not single-select")
                    if width <= 1024 and window.router.get_current_key() != "pos":
                        failures.append(f"{label}/pos: POS not active")
                if key == "returns":
                    returns = screens["returns"]
                    condition_bottom = (
                        returns.cmb_condition.mapTo(returns, QPoint(0, 0)).y()
                        + returns.cmb_condition.height()
                    )
                    reason_top = returns.txt_reason.mapTo(returns, QPoint(0, 0)).y()
                    record["return_form_gap"] = reason_top - condition_bottom
                    # One-pixel Qt border contact is permitted; substantial
                    # negative gaps indicate genuinely overlapping form controls.
                    if record["return_form_gap"] < -3:
                        failures.append(f"{label}/returns: condition and reason inputs overlap")
                checks.append(record)

            if not args.quick and label == "counter_1366":
                for name, key, tab_index in [
                    ("inventory_add_stock", "inventory", 1),
                    ("inventory_alerts", "inventory", 2),
                    ("settings_receipts", "settings", 1),
                    ("settings_staff", "settings", 2),
                    ("settings_recovery", "settings", 3),
                    ("reports_expiry", "reports", 1),
                ]:
                    window.on_nav_clicked(key)
                    screen = screens[key]
                    screen.tabs.setCurrentIndex(tab_index)
                    wait_for_refresh(app, screen)
                    filename = result_dir / label / f"{name}.png"
                    capture(app, window, filename)
                    screenshots.append((name, filename))
                screens["inventory"].tabs.setCurrentIndex(0)
                screens["settings"].tabs.setCurrentIndex(0)
                screens["reports"].tabs.setCurrentIndex(0)

            contact_sheet(screenshots, label.replace("_", " "), result_dir / f"{label}_overview.png")

        if not args.quick:
            # This reports desktop scale emulation only. Actual physical
            # monitor DPI, printer/scanner devices, and workflow with staff
            # are not observable by a hosted CI runner.
            warnings += [
                "QT_SCALE_FACTOR emulates device-pixel ratio, not a physical Windows monitor.",
                "Unattended GUI screenshots require human visual review for aesthetics and full text clipping.",
                "Printer and scanner connections and pharmacy owner acceptance are untested here.",
            ]
        report = {
            "kind": "simulated-offscreen-ui-acceptance",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "qt_scale_factor_env": os.environ.get("QT_SCALE_FACTOR", "default"),
            "primary_screen_dpr": app.primaryScreen().devicePixelRatio() if app.primaryScreen() else None,
            "shop_data": "isolated demo-only, never a live shop",
            "scenarios": len(scenarios),
            "screens_per_scenario": len(screens),
            "screen_checks": checks,
            "critical_failures": failures,
            "limitations": warnings,
        }
        (result_dir / "manifest.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        summary_lines = [
            "# Automated UI acceptance evidence",
            f"Generated: {report['created_utc']}",
            f"Platform: {report['platform']}, Qt scale env: {report['qt_scale_factor_env']}",
            f"Scenarios: {len(scenarios)}, core screens: {len(screens)}, captures: {len(checks)}",
            f"Critical anchor failures: {len(failures)}",
            "",
            "These are headless Qt captures against the isolated demo. Human visual review and actual hardware/pilot acceptance remain mandatory.",
            "",
        ]
        summary_lines += ["- " + failure for failure in failures]
        summary_lines += ["", "## Limitations"] + ["- " + warning for warning in warnings]
        (result_dir / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        print("\n".join(summary_lines), flush=True)
        return 1 if failures and args.strict else 0
    finally:
        # Complete UI workers and release the demo db before process teardown.
        app.processEvents()
        QThreadPool.globalInstance().waitForDone(15000)
        state.clear_user()
        window.close()
        app.processEvents()


if __name__ == "__main__":
    raise SystemExit(collect())
