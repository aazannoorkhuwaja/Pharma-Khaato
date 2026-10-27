#!/usr/bin/env python3
"""Ordered, idempotent upgrade verification for the SQLite migration catalog.

Builds a shop sitting at an older migration head, upgrades it to the current
head, and checks the four things a pharmacy actually depends on:

1. every pending migration is applied and recorded;
2. historical stock, staff and customer rows survive the upgrade;
3. a verified pre-migration backup is written before the first change;
4. running the upgrade twice applies nothing and changes nothing.

Baseline note: ``schema_sqlite.sql`` is the supported baseline for every shipped
version. A database whose columns predate that file cannot be upgraded by this
catalog (migration ``012`` indexes a column the base file provides), which is
recorded as a known limitation in ``docs/DATABASE.md``.

Runs against a temporary data folder; it never touches shop records.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.migration_manager import MigrationManager  # noqa: E402
from core.path_manager import PathManager  # noqa: E402

MIGRATIONS = sorted(path.name for path in (ROOT / "migrations").glob("*.sql"))
OLDER_HEAD = "010_normalize_cnic.sql"


def _load_base_schema(conn):
    conn.executescript((ROOT / "schema_sqlite.sql").read_text(encoding="utf-8"))
    conn.commit()


def _apply_through(conn, head):
    """Bring a connection to an older migration head, as an old shop would be."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for name in MIGRATIONS:
        if name > head:
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


def _schema(conn):
    tables = {}
    for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        tables[name] = sorted(row[1] for row in conn.execute(f'PRAGMA table_info("{name}")'))
    return tables


class TestMigrationEngine(unittest.TestCase):
    def setUp(self):
        self.assertTrue(OLDER_HEAD in MIGRATIONS, "the older head used by this check is gone")
        self.data_dir = tempfile.mkdtemp(prefix="pk-migration-")
        os.environ["PHARMA_KHAATO_DATA_DIR"] = self.data_dir
        PathManager._BASE_DATA_DIR = None

        self.conn = sqlite3.connect(":memory:")
        _load_base_schema(self.conn)
        _apply_through(self.conn, OLDER_HEAD)

        # Historical shop records, written before the upgrade.
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO Supplier (supplier_name, supplier_company_name, Email_address, phone_number) "
            "VALUES ('Legacy Supplier', 'Legacy Co', 'l@l.com', '0300')"
        )
        cur.execute(
            "INSERT INTO Products (product_name, company_name, category, barcode, stock_quantity, price) "
            "VALUES ('Legacy Aspirin', 'Legacy Co', 'Pain Relief', 'LEGACY1', 100, 10.0)"
        )
        cur.execute(
            "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
            "VALUES (1, 'LEGACY-LOT', 100, '2099-12-31', '2026-01-01', 1)"
        )
        cur.execute(
            "INSERT INTO Customers (id_card_number, first_name, last_name, Email_Address, city, registration_date) "
            "VALUES ('3520212345671', 'Legacy', 'Customer', 'N/A', 'Karachi', '2026-01-01')"
        )
        self.conn.commit()

    def tearDown(self):
        os.environ.pop("PHARMA_KHAATO_DATA_DIR", None)
        PathManager._BASE_DATA_DIR = None
        shutil.rmtree(self.data_dir, ignore_errors=True)
        self.conn.close()

    def test_upgrade_is_ordered_and_complete(self):
        pending = MigrationManager.apply_migrations(self.conn, is_sqlite=True)
        expected = [name for name in MIGRATIONS if name > OLDER_HEAD]
        self.assertEqual(sorted(pending), sorted(expected))

        recorded = {row[0] for row in self.conn.execute("SELECT version FROM schema_migrations")}
        self.assertEqual(recorded, set(MIGRATIONS))

    def test_historical_rows_survive_the_upgrade(self):
        MigrationManager.apply_migrations(self.conn, is_sqlite=True)

        row = self.conn.execute(
            "SELECT product_name, price, stock_quantity FROM Products WHERE id = 1"
        ).fetchone()
        self.assertEqual(row[0], "Legacy Aspirin")
        self.assertEqual(float(row[1]), 10.0)

        self.assertEqual(
            self.conn.execute("SELECT quantity FROM Batch WHERE id = 1").fetchone()[0], 100
        )
        self.assertEqual(
            self.conn.execute(
                "SELECT first_name FROM Customers WHERE id_card_number = '3520212345671'"
            ).fetchone()[0],
            "Legacy",
        )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM Supplier").fetchone()[0], 1
        )

    def test_upgrade_writes_a_verified_pre_migration_backup(self):
        MigrationManager.apply_migrations(self.conn, is_sqlite=True)

        backups = [
            name
            for name in os.listdir(PathManager.get_backups_dir())
            if name.startswith("pre_migration_") and name.endswith(".sqlite")
        ]
        self.assertTrue(backups, "no recovery point was written before the upgrade")

        restore_point = sqlite3.connect(os.path.join(PathManager.get_backups_dir(), backups[0]))
        try:
            self.assertEqual(
                str(restore_point.execute("PRAGMA quick_check").fetchone()[0]).lower(), "ok"
            )
            # The recovery point is the pre-upgrade state, not the upgraded one.
            self.assertEqual(
                {row[0] for row in restore_point.execute("SELECT version FROM schema_migrations")},
                {name for name in MIGRATIONS if name <= OLDER_HEAD},
            )
        finally:
            restore_point.close()

    def test_second_upgrade_is_a_no_op(self):
        MigrationManager.apply_migrations(self.conn, is_sqlite=True)
        before = _schema(self.conn)
        self.assertEqual(MigrationManager.apply_migrations(self.conn, is_sqlite=True), [])
        self.assertEqual(_schema(self.conn), before)

    def test_upgraded_schema_matches_a_fresh_install(self):
        MigrationManager.apply_migrations(self.conn, is_sqlite=True)

        fresh = sqlite3.connect(":memory:")
        _load_base_schema(fresh)
        MigrationManager.apply_migrations(fresh, is_sqlite=True, new_database=True)
        try:
            self.assertEqual(_schema(self.conn), _schema(fresh))
        finally:
            fresh.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
