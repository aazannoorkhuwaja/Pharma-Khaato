"""Fresh-install and upgrade paths must agree about the schema.

A shop database is only trustworthy if the database a new pharmacy installs is
built the same way as the database an existing pharmacy upgrades to. These
checks pin the facts that made that fragile: the order the base schema file and
the migration catalog are applied in, the seed rows a fresh shop needs before it
can bill a walk-in customer, and the fact that the only statement failures
swept aside are additive re-declarations.
"""

import logging
import sqlite3
from pathlib import Path

from core.migration_manager import MigrationManager

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = sorted(path.name for path in (ROOT / "migrations").glob("*.sql"))
OLD_SHOP_HEAD = "010_normalize_cnic.sql"


def _base_schema_connection():
    """A new installation: shipped base schema, no migrations recorded yet."""
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "schema_sqlite.sql").read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _tables_and_columns(conn):
    tables = {}
    for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        tables[name] = sorted(row[1] for row in conn.execute(f'PRAGMA table_info("{name}")'))
    return tables


def _apply_through(conn, up_to):
    """Bring a database to an older migration head, as an old shop would be.

    The migrations are executed through the production statement splitter and
    the production tolerance helper, so the result is what a shop that stopped
    upgrading at ``up_to`` genuinely holds — not a list of rows claiming it.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for name in MIGRATIONS:
        if name > up_to:
            break
        statements = MigrationManager._split_statements(
            (ROOT / "migrations" / name).read_text(encoding="utf-8")
        )
        for statement in statements:
            try:
                conn.execute(statement)
            except sqlite3.Error as exc:
                if not MigrationManager._is_tolerated_additive_error(str(exc)):
                    raise
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (name, "2026-01-01T00:00:00"),
        )
    conn.commit()


def test_fresh_install_applies_every_migration(caplog):
    conn = _base_schema_connection()
    with caplog.at_level(logging.WARNING, logger="PharmaKhaatoMigration"):
        applied = MigrationManager.apply_migrations(conn, is_sqlite=True, new_database=True)

    assert sorted(applied) == MIGRATIONS
    recorded = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    assert recorded == set(MIGRATIONS)

    # The base schema is a snapshot superset, so replays are expected — but only
    # additive ones. Anything else must have raised.
    for line in caplog.text.splitlines():
        if "re-declared an existing object" in line:
            assert "duplicate column" in line or "already exists" in line


def test_fresh_install_seeds_walk_in_customers_and_settings():
    conn = _base_schema_connection()
    MigrationManager.apply_migrations(conn, is_sqlite=True, new_database=True)

    customers = {row[0] for row in conn.execute("SELECT id_card_number FROM Customers")}
    assert {"WALKIN", "GUEST_WALK_IN"} <= customers, (
        "a fresh shop cannot bill a walk-in customer without these rows"
    )

    settings = {row[0] for row in conn.execute("SELECT setting_key FROM Pharmacy_Settings")}
    assert {"pharmacy_name", "receipt_footer", "default_tax_rate", "near_expiry_days"} <= settings


def test_only_additive_collisions_are_tolerated():
    assert MigrationManager._is_tolerated_additive_error("duplicate column name: barcode") is True
    assert MigrationManager._is_tolerated_additive_error("table Customer_Returns already exists") is True
    assert MigrationManager._is_tolerated_additive_error('near "SELET": syntax error') is False
    assert MigrationManager._is_tolerated_additive_error("no such column: p.brand_name") is False
    assert MigrationManager._is_tolerated_additive_error("NOT NULL constraint failed: Products.id") is False


def test_shop_that_stopped_upgrading_reaches_todays_schema(fresh_db):
    """A shop sitting at migration 010 must upgrade to the schema a new shop gets."""
    fresh = _base_schema_connection()
    MigrationManager.apply_migrations(fresh, is_sqlite=True, new_database=True)

    stale_shop = _base_schema_connection()
    _apply_through(stale_shop, OLD_SHOP_HEAD)
    pending = MigrationManager.apply_migrations(stale_shop, is_sqlite=True, new_database=False)

    expected_pending = [name for name in MIGRATIONS if name > OLD_SHOP_HEAD]
    assert sorted(pending) == sorted(expected_pending)
    assert _tables_and_columns(stale_shop) == _tables_and_columns(fresh)
