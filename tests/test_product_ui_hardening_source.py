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


def test_credit_screen_uses_task_language_currency_and_one_selected_row_action():
    source = read("ui/screens/khatoo_screen.py")
    assert '["Customer", "Phone", "Area", "Unpaid Bills", "Balance"]' in source
    assert 'QPushButton("Record Payment")' in source
    assert 'setCellWidget(row' not in source
    assert 'Balance: Rs.' in source
    assert "Credit Ref:" not in source
    assert 'setPrefix("Rs. ")' in source
    assert "Qt.ItemDataRole.UserRole" in source


def test_customer_directory_is_task_relevant_not_database_shaped():
    source = read("ui/screens/customer_screen.py")
    assert '["Customer", "Phone", "Area", "Amount Due"]' in source
    assert '"EMAIL"' not in source
    assert "Rs. {float(debt):.2f}" in source


def test_inventory_uses_one_selected_product_action_and_lazy_intake():
    source = read("ui/screens/inventory_screen.py")
    assert "Default Supplier" not in source
    assert '["Product", "Price", "In Stock", "Status"]' in source
    assert 'QPushButton("Add Supplier")' in source
    assert 'self.btn_selected_stock = QPushButton("Add Stock")' in source
    assert 'setCellWidget(row' not in source
    assert "catalog_search_timer" in source
    assert "_load_intake_data" in source
    assert "active_batches(300)" in source
    assert "Qt.ItemDataRole.UserRole" in source


def test_cash_screen_does_not_expose_shift_or_movement_ids():
    source = read("ui/screens/cash_session_screen.py")
    assert '["Type", "Amount", "Note", "Time"]' in source
    assert "Staff ID:" not in source
    assert "Shift #" not in source
    assert 'setPrefix("Rs. ")' in source


def test_staff_settings_hide_employee_ids_and_use_selected_row_actions():
    source = read("ui/screens/settings_screen.py")
    assert '["Username", "Staff Member", "Role"]' in source
    assert 'QPushButton("Reset Selected Password")' in source
    assert "setCellWidget(row" not in source
    assert "At least 8 characters" in source
    assert "At least 6 characters" not in source


def test_first_run_setup_matches_eight_character_policy():
    source = read("ui/screens/first_run_wizard.py")
    assert "At least 8 characters" in source
    assert "at least 8 characters" in source
    assert "at least 6 characters" not in source


def test_pos_keeps_shortcuts_but_removes_hotkey_wall_and_internal_batch_ids():
    source = read("ui/screens/pos_screen.py")
    model_source = read("ui/widgets/pos_models.py")
    held_source = read("ui/widgets/pos_widgets.py")

    assert "HotkeyBadge" not in source
    assert 'QShortcut(QKeySequence("F10")' in source
    assert 'QPushButton("Complete Sale")' in source
    assert 'QPushButton("Complete Sale (F10)")' not in source
    assert 'setPrefix("Rs. ")' in source
    assert "Medicine not found" in source
    assert "Medicine found, but no stock is available for sale" in source
    assert "No shift open" in source
    assert 'HEADERS = ["Product", "Expiry", "In Stock", "Price", "Unit"]' in model_source
    assert "Batch #" not in model_source
    assert 'setHorizontalHeaderLabels(["Held At", "Customer", "Items", "Total"])' in held_source
    assert "import json" in held_source


def test_reports_export_visible_business_columns_only():
    source = read("ui/screens/reports_screen.py")
    assert "_visible_headers" in source
    assert "_visible_row" in source
    assert "isColumnHidden" in source
