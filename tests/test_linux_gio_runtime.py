"""Frozen runtime must not load host plugins against bundled GLib libraries."""
from pathlib import Path
import runpy
import sys
import pytest

HOOK=Path(__file__).resolve().parents[1]/'packaging/hooks/linux_gio.py'


def test_frozen_linux_uses_only_its_own_module_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(tmp_path),raising=False)
    monkeypatch.setattr(sys,'platform','linux')
    monkeypatch.setenv('GIO_MODULE_DIR','/unrelated/system/modules')
    monkeypatch.setenv('GIO_EXTRA_MODULES','/unrelated/extra')
    (tmp_path/'gio-modules').mkdir()
    runpy.run_path(str(HOOK))
    import os
    assert os.environ['GIO_MODULE_DIR']==str(tmp_path/'gio-modules')
    assert 'GIO_EXTRA_MODULES' not in os.environ


def test_source_runtime_preserves_desktop_environment(monkeypatch):
    monkeypatch.setattr(sys,'frozen',False,raising=False)
    monkeypatch.setenv('GIO_MODULE_DIR','/source/host/modules')
    monkeypatch.setenv('GIO_EXTRA_MODULES','/source/host/extra')
    runpy.run_path(str(HOOK))
    import os
    assert os.environ['GIO_MODULE_DIR']=='/source/host/modules'
    assert os.environ['GIO_EXTRA_MODULES']=='/source/host/extra'


def test_incomplete_frozen_package_fails_with_actionable_message(tmp_path, monkeypatch):
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(tmp_path),raising=False)
    monkeypatch.setattr(sys,'platform','linux')
    with pytest.raises(RuntimeError,match='Reinstall'):
        runpy.run_path(str(HOOK))
