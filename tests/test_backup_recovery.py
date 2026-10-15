"""Regression coverage for backup retention and database recovery paths."""

import os
import sqlite3
import time

import pytest


def _make_valid_sqlite(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS marker (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()


def test_daily_backup_prunes_old_autos_but_preserves_safety_files(fresh_db):
    from core import backup_service
    from core.path_manager import PathManager

    backup_dir = PathManager.get_backups_dir()
    os.makedirs(backup_dir, exist_ok=True)

    now = time.time()
    auto_paths = []
    for idx in range(5):
        path = os.path.join(
            backup_dir,
            f"{backup_service.AUTO_BACKUP_PREFIX}_test_{idx}.sqlite",
        )
        _make_valid_sqlite(path)
        # All are recent enough to exercise the early-return path; newest wins.
        stamp = now - idx
        os.utime(path, (stamp, stamp))
        auto_paths.append(path)

    manual = os.path.join(backup_dir, "pharmacy_db_backup_manual.sqlite")
    pre_migration = os.path.join(backup_dir, "pre_migration_test.sqlite")
    _make_valid_sqlite(manual)
    _make_valid_sqlite(pre_migration)

    ok, selected = backup_service.ensure_daily_backup(retention=3)

    assert ok
    assert selected == auto_paths[0]
    remaining_autos = [
        name
        for name in os.listdir(backup_dir)
        if name.startswith(backup_service.AUTO_BACKUP_PREFIX + "_")
        and name.endswith(".sqlite")
    ]
    assert len(remaining_autos) == 3
    assert os.path.exists(manual)
    assert os.path.exists(pre_migration)


def test_restore_integrity_failure_reports_safety_backup(fresh_db, tmp_path, monkeypatch):
    from core import backup_service, db_engine

    # Ensure the live database exists before the restore attempt.
    conn = db_engine.get_conn()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS restore_marker (value TEXT)")
    conn.commit()
    db_engine.reset_thread_connections()

    source_backup = tmp_path / "candidate.sqlite"
    _make_valid_sqlite(source_backup)
    safety_backup = tmp_path / "pre_restore_safety.sqlite"

    original_validate = backup_service._validate_sqlite_database

    def validate(path):
        if os.path.abspath(str(path)) == os.path.abspath(db_engine.PathManager.get_db_path()):
            return False, "forced post-restore quick-check failure"
        return original_validate(str(path))

    monkeypatch.setattr(backup_service, "_validate_sqlite_database", validate)
    monkeypatch.setattr(
        backup_service,
        "backup_database",
        lambda prefix="pharmacy_db_backup": (True, str(safety_backup)),
    )

    ok, message = backup_service.restore_database(str(source_backup))

    assert not ok
    assert str(safety_backup) in message
    assert "docs/RECOVERY.md" in message


def test_failed_migration_rolls_back_and_reports_recovery_path(tmp_path, monkeypatch):
    from core.migration_manager import MigrationManager

    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES ('001_old.sql', 'now')"
        )
        conn.commit()

        bad_migration = tmp_path / "999_failure.sql"
        bad_migration.write_text(
            "CREATE TABLE should_rollback(id INTEGER);\n"
            "INSERT INTO table_that_does_not_exist VALUES (1);\n",
            encoding="utf-8",
        )
        recovery = tmp_path / "pre_migration_recovery.sqlite"

        monkeypatch.setattr(
            MigrationManager,
            "_migration_catalog",
            classmethod(lambda cls, _mig_dir: [str(bad_migration)]),
        )
        monkeypatch.setattr(
            MigrationManager,
            "_create_pre_migration_backup",
            classmethod(lambda cls, _raw_conn, _next: str(recovery)),
        )

        with pytest.raises(RuntimeError) as excinfo:
            MigrationManager.apply_migrations(conn)

        message = str(excinfo.value)
        assert str(recovery) in message
        assert "docs/RECOVERY.md" in message
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='should_rollback'"
        ).fetchone()
        assert exists is None
    finally:
        conn.close()
