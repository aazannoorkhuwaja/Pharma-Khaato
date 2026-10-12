from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_sidebar_keeps_shortcuts_functional_but_out_of_visible_labels():
    source = read("ui/app/main_window.py")
    assert 'btn.setText(f"{text}  {shortcut_key}")' not in source
    assert "QShortcut(QKeySequence(shortcut_key)" in source
    assert 'replace("&", "&&")' in source


def test_shared_table_polish_does_not_stretch_action_column():
    source = read("ui/widgets/table_polish.py")
    assert "setStretchLastSection(False)" in source
    assert '"ref #"' in source
    assert '"id"' in source
    assert "ResizeToContents" in source


def test_credit_screen_uses_task_language_and_currency_formatting():
    source = read("ui/screens/khatoo_screen.py")
    assert '"Balance"' in source
    assert '"Payment"' in source
    assert 'f"Rs. {float(amount_due):.2f}"' in source
    assert "Credit Ref:" not in source
    assert 'setPrefix("Rs. ")' in source
