"""Disposable-store security and crash-retry regressions."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


def test_second_process_cannot_open_owned_store(seeded_shop):
    from core.path_manager import PathManager
    path = PathManager.get_db_path()
    code = 'from core.store_ownership import acquire_store; acquire_store(__import__("sys").argv[1])'
    result = subprocess.run([sys.executable, '-c', code, path], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'already open in another process' in result.stderr


def test_process_exit_releases_ownership(tmp_path):
    from core.store_ownership import acquire_store
    path = str(tmp_path / 'other.sqlite')
    result = subprocess.run([sys.executable, '-c',
        'from core.store_ownership import acquire_store; acquire_store(__import__("sys").argv[1])', path], capture_output=True)
    assert result.returncode == 0, result.stderr
    acquire_store(path)


def test_backup_requires_matching_independent_key(seeded_shop, monkeypatch):
    from core.backup_service import backup_database
    from core.backup_trust import verify_snapshot
    from core.path_manager import PathManager
    from core.recovery_service import recover_from_backup
    ok, path = backup_database()
    assert ok, path
    assert verify_snapshot(path)
    key = Path(PathManager.get_config_dir()) / 'recovery.key'
    original = key.read_bytes()
    key.write_bytes(b'x' * 32)
    assert not verify_snapshot(path)
    ok, message = recover_from_backup(path, 'admin', 'secret123')
    assert not ok and 'cannot be authenticated' in message
    key.write_bytes(original)
    assert verify_snapshot(path)
    with open(path, 'ab') as stream:
        stream.write(b'tampered')
    assert not verify_snapshot(path)


def test_unsigned_backup_cannot_authorize_itself(seeded_shop, tmp_path):
    import sqlite3
    from core.recovery_service import recover_from_backup
    path = tmp_path / 'foreign.sqlite'
    with sqlite3.connect(path) as target:
        seeded_shop.get_conn().raw_conn.backup(target)
    ok, message = recover_from_backup(str(path), 'admin', 'secret123')
    assert not ok and 'cannot be authenticated' in message


def test_stock_postcommit_retry_keeps_identity(seeded_shop, admin_emp_id, monkeypatch):
    from core import inventory_service as stock
    from core.local_operations import perform, pending
    original = stock.clear_inventory_cache
    def fail():
        raise OSError('response lost')
    monkeypatch.setattr(stock, 'clear_inventory_cache', fail)
    callback = lambda op: stock.add_batch(1, 1, 7, '2099-12-31', operation_key=op, employee_id=admin_emp_id)
    with pytest.raises(RuntimeError, match='unknown'):
        perform(admin_emp_id, 'receipt', {'qty':7}, callback, domain='stock')
    assert pending(admin_emp_id, 'stock')
    monkeypatch.setattr(stock, 'clear_inventory_cache', original)
    assert perform(admin_emp_id, 'receipt', {'qty':7}, callback, domain='stock')[0]
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT stock_quantity FROM Products WHERE id=1')
        assert cur.fetchone()[0] == 107


@pytest.mark.skipif(os.name != 'posix', reason='POSIX permissions; Windows ACL acceptance separate')
def test_sensitive_directories_are_private(seeded_shop):
    from core.path_manager import PathManager
    for name in ('data','logs','backups','receipts','exports','config'):
        assert (Path(PathManager.get_base_data_dir()) / name).stat().st_mode & 0o077 == 0


def test_tls_deadline_releases_slot_on_failed_handshake():
    from core.bounded_http import BoundedTLSHTTPServer
    from unittest.mock import Mock
    import threading
    server = object.__new__(BoundedTLSHTTPServer)
    server.timeout_seconds = .1
    server._slots = threading.BoundedSemaphore(1)
    server._slots.acquire()
    connection = Mock()
    connection.do_handshake.side_effect = OSError('disconnected')
    server.context = Mock()
    server.context.wrap_socket.return_value = connection
    server.finish_request = Mock()
    server.shutdown_request = Mock()
    raw = Mock()
    server.process_request_thread(raw, ('127.0.0.1', 123))
    raw.settimeout.assert_called_once_with(.1)
    server.finish_request.assert_not_called()
    server.shutdown_request.assert_called_once_with(connection)
    assert server._slots.acquire(blocking=False)


def test_abandoned_login_attempts_expire(seeded_shop, monkeypatch):
    from core import auth_service
    auth_service._record_failed_attempt('unknown-single-attempt')
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT last_attempt FROM Login_Lockout WHERE username=%s', ('unknown-single-attempt',))
        recorded = cur.fetchone()[0]
    monkeypatch.setattr(auth_service.time, 'time', lambda: recorded + 3601)
    auth_service._prune_expired_lockouts()
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT COUNT(*) FROM Login_Lockout WHERE username=%s', ('unknown-single-attempt',))
        assert cur.fetchone()[0] == 0


def test_settings_load_does_not_block_qt_event_loop(tmp_path):
    code = r'''
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThreadPool
import ui.screens.settings_screen as module
app = QApplication([])
release = threading.Event()
finished = threading.Event()
def delayed(*args, **kwargs):
    release.wait(5)
    finished.set()
    return {}
module._SETTINGS_CONTROLLER.get_many = delayed
screen = module.SettingsScreen(show_message_box=False)
assert not finished.is_set(), 'Settings constructor blocked on the service call'
assert screen._settings_busy
observed = []
def tick():
    observed.append(not finished.is_set())
    release.set()
    app.quit()
QTimer.singleShot(0, tick)
QTimer.singleShot(4000, app.quit)
app.exec()
assert observed == [True], 'GUI event loop did not run during the settings read'
QThreadPool.globalInstance().waitForDone(5000)
app.processEvents()
assert screen._settings_loaded and not screen._settings_busy
screen.close()
'''
    env = {**os.environ, 'QT_QPA_PLATFORM':'offscreen', 'PHARMA_KHAATO_DATA_DIR':str(tmp_path / 'isolated-ui')}
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_received_stock_cannot_be_relabelled_as_another_unit(seeded_shop, admin_emp_id):
    from core.inventory_service import update_product
    ok, message = update_product(1, name='TestMed', price=15, base_unit='bottle', employee_id=admin_emp_id)
    assert not ok and 'base unit cannot change' in message
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT base_unit,stock_quantity FROM Products WHERE id=1')
        assert cur.fetchone() == ('unit', 100)
