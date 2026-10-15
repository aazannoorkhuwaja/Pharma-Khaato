"""Regression guards for product copy and UI/domain separation."""

from pathlib import Path

from ui.ux_copy import NAV_ITEMS, PAYMENT_OPTIONS, CASH_MOVEMENT_OPTIONS, ROLE_OPTIONS


ROOT = Path(__file__).resolve().parents[1]


def test_navigation_uses_task_language_and_has_help_text():
    labels = [item.label for item in NAV_ITEMS]
    assert labels == [
        "New Sale", "Customers", "Customer Credit", "Stock & Products",
        "Shift & Cash", "Reports", "Settings", "Returns & Refunds",
    ]
    assert all(item.help_text.strip() for item in NAV_ITEMS)
    assert all(item.shortcut.startswith("Alt+") for item in NAV_ITEMS)


def test_friendly_payment_labels_are_decoupled_from_backend_values():
    mapping = dict(PAYMENT_OPTIONS)
    assert mapping["Customer Credit"] == "Khatoo Credit"
    assert mapping["Card"] == "Credit Card"
    assert "Khatoo Credit" not in mapping


def test_friendly_cash_and_role_labels_keep_stable_domain_values():
    assert dict(CASH_MOVEMENT_OPTIONS)["Cash In"] == "CASH_IN"
    assert dict(CASH_MOVEMENT_OPTIONS)["Cash Out"] == "CASH_OUT"
    assert dict(ROLE_OPTIONS)["Cashier"] == "Salesman"
    assert dict(ROLE_OPTIONS)["Administrator"] == "Admin"


def test_old_jargon_does_not_return_to_primary_ui_copy():
    ui_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "ui").rglob("*.py")
        if path.name not in {"ux_copy.py"}
    )
    forbidden = [
        "POS Billing Counter",
        "Inventory Master",
        "Control Panel & System Settings",
        "Technical Diagnostics & Logs (Admin / IT)",
        "Recall Selected Sale",
        "Cash Register Reconciliation",
        "FEFO Available Batches List",
        "Debt Profile & Aging",
    ]
    for phrase in forbidden:
        assert phrase not in ui_text, f"Developer-facing wording returned to the UI: {phrase}"


def test_support_diagnostics_are_progressively_disclosed():
    source = (ROOT / "ui" / "screens" / "settings_screen.py").read_text(encoding="utf-8")
    assert 'QPushButton("Show Diagnostics")' in source
    assert "self.txt_tech_log.hide()" in source
    assert "def toggle_technical_details" in source
    assert '"Hide Diagnostics" if visible else "Show Diagnostics"' in source


def test_pos_payment_summary_is_scroll_safe_and_checkout_stays_pinned():
    source = (ROOT / "ui" / "screens" / "pos_screen.py").read_text(encoding="utf-8")
    assert "summary_scroll = QScrollArea()" in source
    assert "right_layout.addWidget(summary_scroll, 1)" in source
    assert source.index("right_layout.addWidget(summary_scroll, 1)") < source.index("self.btn_checkout = QPushButton")


def test_pos_financial_labels_use_theme_safe_semantic_tones():
    source = (ROOT / "ui" / "screens" / "pos_screen.py").read_text(encoding="utf-8")
    assert 'set_tone(self.lbl_subtotal, "primary", "bold")' in source
    assert 'set_tone(self.lbl_tax, "secondary", "bold")' in source
    assert 'set_tone(self.lbl_change, "success", "bold")' in source
