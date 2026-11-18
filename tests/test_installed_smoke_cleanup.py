"""Exercise Windows-style file locks in the disposable installed-app check."""
import os
import subprocess
import sys
from pathlib import Path


def test_smoke_closes_all_temporary_handles_before_cleanup(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r'''
import logging
import tempfile
import sqlite3
import sys
from pathlib import Path
connections = []
OriginalConnect = sqlite3.connect
class TrackedConnection(sqlite3.Connection):
    def close(self):
        super().close()
        self.check_closed = True
def tracked_connect(*args, **kwargs):
    kwargs['factory'] = TrackedConnection
    conn = OriginalConnect(*args, **kwargs)
    conn.check_closed = False
    conn.check_path = conn.execute('PRAGMA database_list').fetchone()[2]
    connections.append(conn)
    return conn
sqlite3.connect = tracked_connect
sys.path.insert(0, sys.argv[1])
OriginalTemporaryDirectory = tempfile.TemporaryDirectory
class WindowsTemporaryDirectory(OriginalTemporaryDirectory):
    def cleanup(self):
        directory = Path(self.name).resolve()
        loggers = [logging.getLogger()] + [value for value in logging.Logger.manager.loggerDict.values() if isinstance(value, logging.Logger)]
        for logger in loggers:
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler) and handler.stream is not None:
                    if Path(handler.baseFilename).resolve().is_relative_to(directory):
                        raise PermissionError('Windows cannot delete an open log file: ' + handler.baseFilename)
        for connection in connections:
            if not connection.check_closed and Path(connection.check_path).resolve().is_relative_to(directory):
                raise PermissionError('Windows cannot delete an open SQLite database: ' + connection.check_path)
        from core.store_ownership import _HANDLES
        for store, (_pid, handle) in _HANDLES.items():
            if not handle.closed and Path(store).resolve().is_relative_to(directory):
                raise PermissionError('Windows cannot delete an open store ownership lock: ' + store)
        super().cleanup()
tempfile.TemporaryDirectory = WindowsTemporaryDirectory
from core.installed_smoke import run
result = run()
from PySide6.QtWidgets import QApplication
assert not QApplication.topLevelWidgets(), 'Disposable windows survived the check'
raise SystemExit(result)
'''
    environment = os.environ.copy()
    environment['PHARMA_KHAATO_DATA_DIR'] = str(tmp_path / 'smoke-envelope')
    environment['QT_QPA_PLATFORM'] = 'offscreen'
    environment['PYTHONFAULTHANDLER'] = '1'
    result = subprocess.run([sys.executable, '-c', script, str(root)], cwd=tmp_path,
                            env=environment, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr[-8000:]


def test_release_disposable_store_keeps_other_store_owned(tmp_path):
    from core.store_ownership import acquire_store, release_store, _HANDLES
    disposable = tmp_path / 'disposable' / 'shop.sqlite'
    other = tmp_path / 'other' / 'shop.sqlite'
    acquire_store(disposable)
    acquire_store(other)
    disposable_handle = _HANDLES[str(disposable.resolve())][1]
    other_handle = _HANDLES[str(other.resolve())][1]
    try:
        release_store(disposable)
        release_store(disposable)  # Cleanup is safe to repeat after partial failure.
        assert disposable_handle.closed
        assert not other_handle.closed
        assert (disposable.parent / '.shop-owner.lock').exists()
        assert str(other.resolve()) in _HANDLES
    finally:
        release_store(disposable)
        release_store(other)


def test_cleanup_keeps_logs_outside_disposable_shop(tmp_path):
    import logging
    from core.installed_smoke import _close_temporary_log_handlers
    temporary = tmp_path / 'disposable'
    temporary.mkdir()
    own = logging.FileHandler(temporary / 'check.log')
    outside = logging.FileHandler(tmp_path / 'keep.log')
    logger = logging.getLogger('smoke-cleanup-scope-check')
    logger.addHandler(own)
    logger.addHandler(outside)
    try:
        _close_temporary_log_handlers(temporary)
        assert own.stream is None and own not in logger.handlers
        assert outside in logger.handlers and outside.stream is not None
    finally:
        for handler in (own, outside):
            logger.removeHandler(handler)
            handler.close()


def test_failed_windowed_check_writes_report_instead_of_raising(fresh_db, tmp_path, monkeypatch):
    import json
    import main
    from core import installed_smoke
    report = tmp_path / 'result.json'
    def locked_file():
        raise PermissionError('Windows locked test log')
    monkeypatch.setattr(installed_smoke, 'run', locked_file)
    monkeypatch.setattr(main, 'install_global_exception_hook', lambda:None)
    monkeypatch.setattr(main, 'check_gui', lambda:None)
    monkeypatch.setattr(sys, 'argv', ['pharma_khaato.exe','--functional-smoke','--headless','--smoke-report',str(report)])
    assert main.main() == 2
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['ok'] is False
    assert result['error'] == 'Windows locked test log'
    assert 'PermissionError' in result['traceback']
