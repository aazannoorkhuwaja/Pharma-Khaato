#!/usr/bin/env python3
"""Static UI quality guard for responsive-design regressions.

Run with: python scripts/ui_audit.py
No PySide6 installation is required.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "ui" / "screens"

checks = []

literal_fonts = []
fixed_panels = []
for path in SCREENS.glob("*.py"):
    text = path.read_text(encoding="utf-8")
    if re.search(r"font-size\s*:\s*\d+px", text):
        literal_fonts.append(path.name)
    if ".setFixedWidth(" in text or ".setFixedSize(" in text:
        fixed_panels.append(path.name)

checks.append(("No screen-level literal pixel font sizes", not literal_fonts, literal_fonts))
checks.append(("No fixed-width/fixed-size business panels", not fixed_panels, fixed_panels))

theme = (ROOT / "ui" / "theme" / "theme_manager.py").read_text(encoding="utf-8")
checks.append(("Theme scales control height", "LayoutMetrics.CONTROL_HEIGHT" in theme, []))
checks.append(("Theme provides compact table actions", 'QPushButton[compact="true"]' in theme, []))
checks.append(("Theme provides semantic metrics", "QLabel#metricLarge" in theme, []))

shell = (ROOT / "ui" / "app" / "main_window.py").read_text(encoding="utf-8")
checks.append(("Adaptive shell has full/compact/mini modes", all(x in shell for x in ['"full"', '"compact"', '"mini"']), []))

failed = False
for label, ok, details in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if details:
        print("       " + ", ".join(details))
    failed |= not ok

raise SystemExit(1 if failed else 0)
