"""Launch/demo safety regression tests."""

import sqlite3
from pathlib import Path


def test_migration_versions_are_unique():
    from core.migration_manager import MigrationManager

    root = Path(__file__).resolve().parents[1]
    catalog = MigrationManager._migration_catalog(str(root / "migrations"))
    versions = [Path(path).name.split("_", 1)[0] for path in catalog]
    assert len(versions) == len(set(versions))


def test_trigger_migration_is_not_split_inside_begin_end_block():
    from core.migration_manager import MigrationManager

    root = Path(__file__).resolve().parents[1]
    sql = (root / "migrations" / "017_checkout_request_lifecycle.sql").read_text(
        encoding="utf-8"
    )
    statements = MigrationManager._split_statements(sql)

    assert len(statements) == 3
    trigger_sql = statements[-1]
    assert trigger_sql.lstrip().startswith("CREATE TRIGGER")
    assert trigger_sql.rstrip().endswith("END;")
    assert trigger_sql.count("UPDATE ") == 2

    # Execute the parsed migration against the smallest compatible schema so
    # this regression test catches both accidental splitting and trigger syntax errors.
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TABLE Employee (Employee_id INTEGER PRIMARY KEY)")
    conn.execute(
        "CREATE TABLE Purchase (id INTEGER PRIMARY KEY, employee_id INTEGER, checkout_token TEXT)"
    )
    for statement in statements:
        conn.execute(statement)
    trigger = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name = ?",
        ("purchase_checkout_request_ai",),
    ).fetchone()
    conn.close()
    assert trigger == ("purchase_checkout_request_ai",)


def test_readiness_passes_on_fresh_database(fresh_db):
    from core.readiness_service import run_readiness_checks

    # Force schema/migrations before checking it.
    conn = fresh_db.get_conn()
    conn.close()
    report = run_readiness_checks()
    assert report["ok"], report
    assert report["failed_count"] == 0


def test_checkout_retry_returns_original_sale_once(seeded_shop, admin_emp_id, cash_shift):
    from core.checkout_idempotency_service import process_checkout_idempotently
    from core.pos_service import CheckoutRequest, POSTransactionEngine

    token = "launch-readiness-retry-token"
    request = CheckoutRequest(
        customer_id="WALKIN",
        employee_id=admin_emp_id,
        cart=[{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 2}],
        payment_method="Cash",
        total=30.0,
    )
    request.checkout_token = token

    first = process_checkout_idempotently(request, POSTransactionEngine.process_checkout)
    second = process_checkout_idempotently(request, POSTransactionEngine.process_checkout)

    assert first.success, first.message
    assert second.success, second.message
    assert second.purchase_id == first.purchase_id
    assert "Duplicate submission prevented" in second.message

    conn = seeded_shop.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM Purchase WHERE checkout_token = ?", (token,))
    count, min_id, max_id = cur.fetchone()
    assert count == 1
    assert min_id == max_id == first.purchase_id
    cur.execute("SELECT stock_quantity FROM Products WHERE id = 1")
    assert cur.fetchone()[0] == 98

    request.cart[0]["qty"] = 3
    altered = process_checkout_idempotently(request, POSTransactionEngine.process_checkout)
    assert not altered.success and altered.outcome == "rejected"
    cur.execute("SELECT COUNT(*) FROM Purchase")
    assert cur.fetchone()[0] == 1


def test_new_checkout_token_preserves_other_counter_pending(seeded_shop, admin_emp_id):
    from core.checkout_idempotency_service import prepare_checkout

    assert prepare_checkout("old-pending-token", admin_emp_id)[0]
    assert prepare_checkout("new-pending-token", admin_emp_id)[0]

    conn = seeded_shop.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status FROM Checkout_Request WHERE token = 'old-pending-token'")
    assert cur.fetchone()[0] == "PENDING"
    cur.execute("SELECT status FROM Checkout_Request WHERE token = 'new-pending-token'")
    assert cur.fetchone()[0] == "PENDING"
