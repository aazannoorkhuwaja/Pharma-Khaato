"""Source-level regression guards for the first-run setup experience.

These tests avoid importing Qt so they can run in backend-only CI while still
protecting the layout decisions that fixed the maximised light-theme wizard.
"""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "ui" / "screens" / "first_run_wizard.py").read_text(encoding="utf-8")


def test_setup_uses_global_theme_not_stale_local_palette():
    assert "self.setStyleSheet" not in SRC
    assert "ThemeTokens" not in SRC
    assert 'setObjectName("card")' in SRC


def test_setup_caps_reading_width_and_reflows_fields():
    assert "FORM_MAX_WIDTH = 960" in SRC
    assert "TWO_COLUMN_AT = 860" in SRC
    assert "def resizeEvent" in SRC
    assert "_apply_form_layout" in SRC


def test_setup_has_scrollable_content_and_non_overlapping_footer():
    assert 'setObjectName("setupScroll")' in SRC
    assert 'setObjectName("setupFooter")' in SRC
    assert 'QPushButton("Complete setup")' in SRC


def test_setup_copy_is_task_focused_and_marks_required_fields():
    assert 'QLabel("Set up your pharmacy")' in SRC
    assert 'QLabel("Fields marked * are required.")' in SRC
    assert '"Pharmacy details"' in SRC
    assert '"Owner account"' in SRC
