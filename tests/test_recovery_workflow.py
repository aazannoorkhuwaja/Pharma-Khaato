"""Recovery must work when normal pharmacy startup cannot."""
import os
import sqlite3
import time
from pathlib import Path

import pytest


def test_full_durability_and_bounded_cache(fresh_db, monkeypatch):
    monkeypatch.setenv("PHARMA_KHAATO_CACHE_KIB", "999999")
    conn = fresh_db.get_conn().raw_conn
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert conn.execute("PRAGMA cache_size").fetchone()[0] == -32768


def test_nested_helpers_cannot_commit_outer_transaction(fresh_db):
    from core.db_engine import get_db
    with pytest.raises(RuntimeError):
        with get_db(immediate=True) as (_conn, cur):
            cur.execute("INSERT INTO Pharmacy_Settings(setting_key,setting_value) VALUES('outer-test','1')")
            with get_db() as (_nested, inner):
                inner.execute("SELECT COUNT(*) FROM Pharmacy_Settings")
            raise RuntimeError("abort sale")
    with get_db() as (_conn, cur):
        cur.execute("SELECT setting_value FROM Pharmacy_Settings WHERE setting_key='outer-test'")
        assert cur.fetchone() is None


def test_wrong_application_backup_leaves_live_db_unchanged(seeded_shop, tmp_path):
    from core.backup_service import restore_database
    unrelated = tmp_path / "other.sqlite"
    with sqlite3.connect(unrelated) as conn:
        conn.execute("CREATE TABLE OtherApp(value TEXT)")
    assert not restore_database(str(unrelated))[0]
    assert seeded_shop.get_conn().raw_conn.execute("SELECT COUNT(*) FROM Employee").fetchone()[0] == 1


def test_good_backup_recovers_corrupt_store_and_keeps_evidence(seeded_shop):
    from core.backup_service import backup_database, restore_database
    ok, backup = backup_database()
    assert ok
    live = Path(seeded_shop.PathManager.get_db_path())
    seeded_shop.reset_thread_connections()
    live.write_bytes(b"isolated corrupt database")
    ok, message = restore_database(backup)
    assert ok, message
    assert seeded_shop.get_conn().raw_conn.execute("SELECT COUNT(*) FROM Employee").fetchone()[0] == 1
    evidence = list(Path(seeded_shop.PathManager.get_backups_dir()).glob("before_restore_*/*sqlite"))
    assert any(path.read_bytes().startswith(b"isolated corrupt") for path in evidence)


def test_failed_swap_rolls_back_original_files(seeded_shop, monkeypatch):
    import core.backup_service as backups
    ok, snapshot = backups.backup_database()
    assert ok
    live = seeded_shop.PathManager.get_db_path()
    original_replace = backups.os.replace
    def fail_stage(source, destination):
        if ".restore-" in str(source) and str(destination) == live:
            raise OSError("simulated disk failure")
        return original_replace(source, destination)
    monkeypatch.setattr(backups.os, "replace", fail_stage)
    assert not backups.restore_database(snapshot)[0]
    assert seeded_shop.get_conn().raw_conn.execute("SELECT COUNT(*) FROM Employee").fetchone()[0] == 1


def test_production_restore_blocks_queued_writes(seeded_shop):
    from core.backup_service import backup_database, restore_database
    ok, snapshot = backup_database()
    assert ok and restore_database(snapshot, require_restart=True)[0]
    with pytest.raises(RuntimeError, match="Restart"):
        seeded_shop.get_conn()


def test_first_admin_only_once_and_staff_requires_actor(seeded_shop):
    from core.auth_service import register_initial_admin, create_employee, update_employee_password
    assert not register_initial_admin("another", "password123", "Another", "Owner")[0]
    assert not create_employee("clerk", "password123", "Cash", "Staff")[0]
    assert not update_employee_password(1, "changedpassword")[0]
    assert create_employee("clerk", "password123", "Cash", "Staff", actor_id=1)[0]
    assert not update_employee_password(1, "changedpassword", actor_id=2)[0]


def test_manager_approval_shares_login_lockout_and_audit(seeded_shop):
    from core.auth_service import login_user
    from core.manager_auth_service import verify_manager
    for _ in range(5):
        login_user("admin", "wrong")
    assert verify_manager("admin", "secret123")[0] is None
    assert seeded_shop.get_conn().raw_conn.execute("SELECT COUNT(*) FROM Audit_Log WHERE action='MANAGER_AUTH_FAILED'").fetchone()[0] >= 1


def test_discount_approval_scope_and_single_use(seeded_shop):
    from core.db_engine import get_db
    from core.manager_auth_service import issue_discount_approval, validate_discount_approval
    token, message = issue_discount_approval("admin", "secret123", 1, 20, 100)
    assert token, message
    with get_db(immediate=True) as (_conn, cur):
        assert not validate_discount_approval(cur, token, 1, 21, 100)[0]
        assert validate_discount_approval(cur, token, 1, 20, 100)[0]
        assert not validate_discount_approval(cur, token, 1, 20, 100)[0]


def test_automatic_backup_refreshes_during_uptime(seeded_shop):
    from core.backup_service import ensure_daily_backup
    ok, first = ensure_daily_backup()
    assert ok
    stale = time.time() - 3700
    os.utime(first, (stale, stale))
    ok, second = ensure_daily_backup()
    assert ok and second != first


def test_second_location_receives_verified_snapshot(seeded_shop, tmp_path):
    from core.backup_service import configure_backup_destination, backup_database, _validate_sqlite_database
    second = tmp_path / "protected-device"
    assert configure_backup_destination(str(second))[0]
    ok, local = backup_database()
    assert ok
    copy = second / Path(local).name
    assert copy.exists() and _validate_sqlite_database(str(copy))[0]


def test_prelogin_recovery_authenticates_from_snapshot(seeded_shop):
    from core.backup_service import backup_database
    from core.recovery_service import recover_from_backup
    ok, snapshot = backup_database()
    assert ok
    seeded_shop.reset_thread_connections()
    Path(seeded_shop.PathManager.get_db_path()).write_bytes(b"corrupt live for recovery")
    assert not recover_from_backup(snapshot, "admin", "wrong")[0]
    assert recover_from_backup(snapshot, "admin", "secret123")[0]


def test_interrupted_swap_recovers_original_before_opening(seeded_shop, monkeypatch):
    import core.backup_service as backups
    class SimulatedPowerLoss(BaseException):
        pass
    ok, snapshot = backups.backup_database()
    assert ok
    live = seeded_shop.PathManager.get_db_path()
    original_replace = backups.os.replace
    def interrupted(source, destination):
        if ".restore-" in str(source) and str(destination) == live:
            raise SimulatedPowerLoss()
        return original_replace(source, destination)
    monkeypatch.setattr(backups.os, "replace", interrupted)
    with pytest.raises(SimulatedPowerLoss):
        backups.restore_database(snapshot)
    assert not Path(live).exists()
    assert seeded_shop.get_conn().raw_conn.execute("SELECT COUNT(*) FROM Employee").fetchone()[0] == 1
    assert not (Path(seeded_shop.PathManager.get_config_dir()) / "restore-pending.json").exists()


def test_restore_drains_active_worker_transaction(seeded_shop):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from core.backup_service import backup_database, restore_database
    from core.db_engine import get_db
    ok, snapshot = backup_database()
    assert ok
    writer_started, release_writer, restore_started, restore_finished = Event(), Event(), Event(), Event()
    def writer():
        with get_db(immediate=True) as (_conn, cur):
            cur.execute("UPDATE Products SET product_name='After snapshot' WHERE id=1")
            writer_started.set()
            assert release_writer.wait(5)
    def restore():
        restore_started.set()
        result = restore_database(snapshot)
        restore_finished.set()
        return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        writing = pool.submit(writer)
        assert writer_started.wait(5)
        restoring = pool.submit(restore)
        assert restore_started.wait(5)
        assert not restore_finished.wait(0.05)
        release_writer.set()
        writing.result(timeout=5)
        assert restoring.result(timeout=5)[0]
    assert seeded_shop.get_conn().raw_conn.execute("SELECT product_name FROM Products WHERE id=1").fetchone()[0] == "TestMed"


def test_recovery_screen_opens_without_business_database(qapp, seeded_shop, monkeypatch):
    from ui.screens.recovery_screen import RecoveryDialog
    seeded_shop.reset_thread_connections()
    Path(seeded_shop.PathManager.get_db_path()).write_bytes(b"cannot open")
    monkeypatch.setattr(seeded_shop, "get_conn", lambda: pytest.fail("Recovery UI opened the damaged store"))
    dialog = RecoveryDialog()
    assert dialog.windowTitle() == "Recover Pharmacy Data"
    dialog.deleteLater()


def test_restore_flushes_stage_with_windows_compatible_handle(seeded_shop, monkeypatch):
    """Windows' file commit rejects read-only descriptors with EBADF."""
    import builtins
    import errno
    from core import backup_service as backups
    ok, snapshot = backups.backup_database()
    assert ok
    with seeded_shop.get_db(immediate=True) as (_conn, cur):
        cur.execute("UPDATE Products SET product_name='After backup' WHERE id=1")
    original_sync = backups.os.fsync
    stage_handles = []
    flushed = []
    def track_stage_open(path, mode='r', *args, **kwargs):
        handle = builtins.open(path, mode, *args, **kwargs)
        if '.restore-' in str(path):
            stage_handles.append(handle)
        return handle
    def windows_sync(descriptor):
        for handle in stage_handles:
            if not handle.closed and handle.fileno() == descriptor:
                if not handle.writable():
                    raise OSError(errno.EBADF, 'Bad file descriptor')
                flushed.append(descriptor)
        return original_sync(descriptor)
    monkeypatch.setattr(backups, 'open', track_stage_open, raising=False)
    monkeypatch.setattr(backups.os, 'fsync', windows_sync)
    restored, message = backups.restore_database(snapshot)
    assert restored, message
    assert flushed, 'The staged database must be flushed before replacement.'
    with seeded_shop.get_db() as (_conn, cur):
        cur.execute('SELECT product_name FROM Products WHERE id=1')
        assert cur.fetchone()[0] == 'TestMed'


def test_stage_flush_failure_preserves_live_store(seeded_shop, monkeypatch):
    """A real flush error must abort restore rather than being ignored."""
    import errno
    from core import backup_service as backups
    ok, snapshot = backups.backup_database()
    assert ok
    with seeded_shop.get_db(immediate=True) as (_conn, cur):
        cur.execute("UPDATE Products SET product_name='Keep current records' WHERE id=1")
    def failed_sync(descriptor):
        raise OSError(errno.EIO, 'Simulated disk flush failure')
    monkeypatch.setattr(backups.os, 'fsync', failed_sync)
    assert not backups.restore_database(snapshot)[0]
    assert not (Path(seeded_shop.PathManager.get_config_dir()) / 'restore-pending.json').exists()
    with seeded_shop.get_db() as (_conn, cur):
        cur.execute('SELECT product_name FROM Products WHERE id=1')
        assert cur.fetchone()[0] == 'Keep current records'
