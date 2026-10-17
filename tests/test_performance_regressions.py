"""Regression guards for UI responsiveness and cache correctness."""

from pathlib import Path

from core.data_revision import current, snapshot, touch

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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
    source = read("ui/app/router.py")
    assert "name == self._current_key" in source
    assert "constructor_loads_data" in source
    assert "if not created and self._needs_refresh(name)" in source
    assert "Slow navigation" in source


def test_application_declares_domain_aware_screen_refreshes():
    source = read("ui/app/application.py")
    assert 'domains=("inventory",)' in source
    assert 'domains=("customers", "credit")' in source
    assert 'domains=("cash", "sales", "credit", "returns")' in source
    assert 'domains=("reports", "sales", "inventory", "credit", "returns")' in source
    assert "window.set_active_user(current_user)" not in source


def test_startup_health_check_is_not_on_pre_window_critical_path():
    source = read("ui/app/application.py")
    show_at = source.index("window.show()")
    async_health_at = source.index("startup_tasks.run(")
    assert async_health_at > show_at
    assert "health = app_controller.health()" not in source


def test_pos_and_returns_clear_inventory_read_cache_after_stock_mutations():
    pos = read("controllers/pos_controller.py")
    returns = read("controllers/return_controller.py")
    assert "clear_inventory_cache()" in pos
    assert "clear_inventory_cache()" in returns


def test_hot_searches_are_bounded():
    product_search = read("core/product_search_service.py")
    customers = read("core/customer_directory_service.py")
    credit = read("core/credit_query_service.py")
    inventory = read("core/inventory_query_service.py")
    assert "_MAX_RESULTS" in product_search and "LIMIT" in product_search
    assert "safe_limit" in customers and "LIMIT" in customers
    assert "LIMIT" in credit and "OFFSET" in credit
    assert "product_limit" in inventory and "LIMIT" in inventory
    assert "search_catalog_products" in inventory


def test_heavy_feature_reads_use_shared_worker_runner():
    for rel_path in (
        "ui/screens/reports_screen.py",
        "ui/screens/settings_screen.py",
        "ui/screens/customer_screen.py",
        "ui/screens/inventory_screen.py",
        "ui/screens/khatoo_screen.py",
        "ui/screens/cash_session_screen.py",
    ):
        source = read(rel_path)
        assert "AsyncTaskRunner" in source, rel_path
        assert "run_latest(" in source or "._tasks.run(" in source, rel_path


def test_latest_request_wins_for_rapid_search_and_report_changes():
    source = read("ui/app/async_tasks.py")
    assert "def run_latest(" in source
    assert "self._versions" in source
    assert "if self._versions.get(key) == version" in source


def test_sqlite_lock_wait_is_bounded_for_counter_responsiveness():
    source = read("core/db_engine.py")
    assert "_SQLITE_BUSY_TIMEOUT_MS = 3000" in source
    assert "timeout=_SQLITE_BUSY_TIMEOUT_MS / 1000.0" in source
    assert "PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}" in source


def test_develop_branch_uses_fast_single_environment_ci():
    source = read(".github/workflows/ci.yml")
    assert "develop-fast:" in source
    assert "refs/heads/develop-ui" in source
    assert 'python-version: "3.14"' in source
    assert "full-matrix:" in source
    assert "os: [ubuntu-latest, windows-latest]" in source
