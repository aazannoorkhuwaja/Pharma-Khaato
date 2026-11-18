"""Old 014 performance-index history must remain readable after the 015 rename."""
import sqlite3
from pathlib import Path


def test_backup_accepts_verified_historical_index_alias(seeded_shop, tmp_path):
    from core.backup_service import _validate_sqlite_database
    copied = tmp_path / 'historical.sqlite'
    with sqlite3.connect(copied) as conn:
        seeded_shop.get_conn().raw_conn.backup(conn)
        conn.execute("INSERT INTO schema_migrations(version,applied_at) VALUES('014_ui_performance_indexes.sql','historical')")
    ok, message = _validate_sqlite_database(str(copied))
    assert ok, message


def test_alias_does_not_hide_missing_or_altered_index(seeded_shop, tmp_path):
    from core.backup_service import _validate_sqlite_database
    copied = tmp_path / 'incomplete.sqlite'
    with sqlite3.connect(copied) as conn:
        seeded_shop.get_conn().raw_conn.backup(conn)
        conn.execute("INSERT INTO schema_migrations(version,applied_at) VALUES('014_ui_performance_indexes.sql','historical')")
        conn.execute('DROP INDEX idx_products_active_name')
        conn.execute('CREATE INDEX idx_products_active_name ON Products(company_name)')
    ok, message = _validate_sqlite_database(str(copied))
    assert not ok and 'index definition differs' in message


def test_unknown_migration_and_alias_without_replacement_still_fail():
    import pytest
    from core.migration_manager import MigrationManager
    known={'014_receipt_templates.sql','015_ui_performance_indexes.sql'}
    for history in ({'999_unknown.sql'}, {'014_ui_performance_indexes.sql'}):
        with pytest.raises(ValueError, match='different application version'):
            MigrationManager.canonical_history(history, known)


def test_startup_preserves_historical_rows_and_checksums(seeded_shop):
    from core.migration_manager import MigrationManager
    raw=seeded_shop.get_conn().raw_conn
    raw.execute("INSERT INTO schema_migrations(version,applied_at) VALUES('014_ui_performance_indexes.sql','historical')")
    raw.commit()
    before=raw.execute('SELECT version,applied_at,checksum FROM schema_migrations ORDER BY version').fetchall()
    MigrationManager.apply_migrations(raw)
    assert raw.execute('SELECT version,applied_at,checksum FROM schema_migrations ORDER BY version').fetchall()==before


def test_historical_alias_cannot_claim_unknown_checksum(seeded_shop, tmp_path):
    from core.backup_service import _validate_sqlite_database
    copied=tmp_path/'forged.sqlite'
    with sqlite3.connect(copied) as conn:
        seeded_shop.get_conn().raw_conn.backup(conn)
        conn.execute("INSERT INTO schema_migrations(version,applied_at,checksum) VALUES('014_ui_performance_indexes.sql','historical','invented')")
    ok,message=_validate_sqlite_database(str(copied))
    assert not ok and 'historical migration checksum' in message


def test_observed_legacy_nullable_audit_actor_is_preserved(seeded_shop, tmp_path):
    from core.backup_service import _validate_sqlite_database
    copied=tmp_path/'old-audit.sqlite'
    with sqlite3.connect(copied) as conn:
        seeded_shop.get_conn().raw_conn.backup(conn)
        conn.execute("INSERT INTO schema_migrations(version,applied_at) VALUES('014_ui_performance_indexes.sql','historical')")
        conn.execute('ALTER TABLE Audit_Log RENAME TO Previous_Audit_Log')
        conn.execute('CREATE TABLE Audit_Log(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,user_id TEXT,action TEXT NOT NULL,details TEXT)')
        conn.execute('INSERT INTO Audit_Log SELECT * FROM Previous_Audit_Log')
        conn.execute('DROP TABLE Previous_Audit_Log')
        conn.execute("INSERT INTO Audit_Log(timestamp,user_id,action) VALUES('historical',NULL,'SYSTEM_EVENT')")
    before=copied.read_bytes()
    assert _validate_sqlite_database(str(copied)) == (True,'ok')
    assert copied.read_bytes()==before


def test_foreign_key_comparison_ignores_only_constraint_order():
    from core.schema_validation import _foreign_keys
    with sqlite3.connect(':memory:') as conn:
        conn.executescript('CREATE TABLE A(id INTEGER PRIMARY KEY); CREATE TABLE B(id INTEGER PRIMARY KEY);'
                          'CREATE TABLE First(a REFERENCES A(id),b REFERENCES B(id));'
                          'CREATE TABLE Reordered(a INTEGER,b INTEGER,FOREIGN KEY(b) REFERENCES B(id),FOREIGN KEY(a) REFERENCES A(id));'
                          'CREATE TABLE Wrong(a REFERENCES A(id) ON DELETE CASCADE,b REFERENCES B(id));')
        assert _foreign_keys(conn,'First')==_foreign_keys(conn,'Reordered')
        assert _foreign_keys(conn,'First')!=_foreign_keys(conn,'Wrong')


def test_observed_legacy_hold_employee_constraint_is_verified(seeded_shop, tmp_path):
    from core.backup_service import _validate_sqlite_database
    copied=tmp_path/'old-held-sales.sqlite'
    with sqlite3.connect(copied) as conn:
        seeded_shop.get_conn().raw_conn.backup(conn)
        conn.execute("INSERT INTO schema_migrations(version,applied_at) VALUES('014_ui_performance_indexes.sql','historical')")
        table_sql=conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Hold_Sales'").fetchone()[0]
        indexes=[r[0] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='Hold_Sales' AND sql IS NOT NULL")]
        assert conn.execute('SELECT COUNT(*) FROM Hold_Sales').fetchone()[0]==0
        conn.execute('DROP TABLE Hold_Sales')
        conn.execute(table_sql.rstrip()[:-1]+', FOREIGN KEY(employee_id) REFERENCES Employee(Employee_id) ON DELETE CASCADE)')
        for statement in indexes:conn.execute(statement)
    assert _validate_sqlite_database(str(copied))==(True,'ok')
