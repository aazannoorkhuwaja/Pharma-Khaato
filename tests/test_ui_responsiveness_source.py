"""Source-level guardrails for responsive UI regressions.

These tests deliberately avoid importing PySide6 so they run in backend-only CI
as well as native GUI jobs.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"


def test_screens_do_not_hardcode_literal_font_sizes():
    offenders = []
    pattern = re.compile(r"font-size\s*:\s*\d+px")
    for path in (UI / "screens").glob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert not offenders, f"Literal pixel font sizes bypass ThemeManager scaling: {offenders}"


def test_business_panels_are_not_fixed_width():
    offenders = []
    for path in (UI / "screens").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if ".setFixedWidth(" in text or ".setFixedSize(" in text:
            offenders.append(path.name)
    assert not offenders, f"Fixed business panels break 1024/high-DPI layouts: {offenders}"


def test_theme_scales_controls_and_semantic_typography():
    theme = (UI / "theme" / "theme_manager.py").read_text(encoding="utf-8")
    assert "LayoutMetrics.CONTROL_HEIGHT" in theme
    assert 'QLabel#metricLarge' in theme
    assert 'QLineEdit#primarySearch' in theme
    assert 'QPushButton[compact="true"]' in theme


def test_shell_has_three_responsive_sidebar_modes():
    shell = (UI / "app" / "main_window.py").read_text(encoding="utf-8")
    for mode in ('"full"', '"compact"', '"mini"'):
        assert mode in shell
    assert "SIDEBAR_FULL_AT" in shell
    assert "SIDEBAR_COMPACT_AT" in shell
