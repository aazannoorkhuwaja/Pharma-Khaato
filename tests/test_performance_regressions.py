"""Regression guards for UI responsiveness and cache correctness."""

from pathlib import Path

from core.data_revision import current, snapshot, touch

ROOT = Path(__file__).resolve().parents[1]


def test_data_revision_changes_only_touched_domains():
    before_inventory = current("perf_test_inventory")
    before_cash = current("perf_test_cash")
    touch("perf_test_inventory")
    assert current("perf_test_inventory") == before_inventory + 1
    assert current("perf_test_cash") == before_cash


def test_revision_snapshot_is_stable_and_comparable():
    domains = ("perf_test_sales", "perf_test_inventory_2")
    first = snapshot(domains)
    assert first == snapshot(reversed(domains))
    touch("perf_test_sales")
    assert snapshot(domains) != first


def test_router_does_not_reload_active_screen_or_duplicate_first_factory_load():
    source = (ROOT / "ui" / "app" / "router.py").read_text(encoding="utf-8")
    assert "name == self._current_key" in source
    assert "constructor_loads_data" in source
    assert "if not created and self._needs_refresh(name)" in source
    assert "Slow navigation" in source


def test_application_declares_domain_aware_screen_refreshes():
    source = (ROOT / "ui" / "app" / "application.py").read_text(encoding="utf-8")
    assert 'domains=("inventory",)' in source
    assert 'domains=("customers", "credit")' in source
    assert 'domains=("cash", "sales", "credit", "returns")' in source
    assert 'domains=("reports", "sales", "inventory", "credit", "returns")' in source
    # MainWindow already initializes the current user. Repeating this in
    # run_app used to query the active shift twice during startup.
    assert "window.set_active_user(current_user)" not in source


def test_pos_and_returns_clear_inventory_read_cache_after_stock_mutations():
    pos = (ROOT / "controllers" / "pos_controller.py").read_text(encoding="utf-8")
    returns = (ROOT / "controllers" / "return_controller.py").read_text(encoding="utf-8")
    assert "clear_inventory_cache()" in pos
    assert "clear_inventory_cache()" in returns


def test_hot_searches_are_bounded():
    product_search = (ROOT / "core" / "product_search_service.py").read_text(encoding="utf-8")
    customers = (ROOT / "core" / "customer_directory_service.py").read_text(encoding="utf-8")
    credit = (ROOT / "core" / "credit_query_service.py").read_text(encoding="utf-8")
    assert "_MAX_RESULTS" in product_search and "LIMIT" in product_search
    assert "safe_limit" in customers and "LIMIT" in customers
    assert "safe_limit" in credit and "LIMIT" in credit
