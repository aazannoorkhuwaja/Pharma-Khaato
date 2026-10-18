"""Windows delivery checks that can also run on a Linux development machine."""
import json
import sys
from types import SimpleNamespace

import pytest


def test_windows_shop_data_is_per_user_and_outside_install_folder(tmp_path, monkeypatch):
    from core.path_manager import PathManager
    import core.path_manager as paths
    monkeypatch.delenv('PHARMA_KHAATO_DATA_DIR', raising=False)
    monkeypatch.delenv('PHARMA_KHAATO_DEV_WORKSPACE', raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'Windows User Data'))
    monkeypatch.setattr(paths.platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(PathManager, '_BASE_DATA_DIR', None)
    expected = tmp_path / 'Windows User Data' / 'Pharma-Khaato'
    assert PathManager.get_base_data_dir() == str(expected)
    assert (expected / 'data').is_dir()
    assert 'Programs' not in PathManager.get_db_path()


@pytest.mark.parametrize('report,expected_code', [(None,4),({'ok':False},4),('valid',0)])
def test_windowed_executable_requires_a_positive_functional_report(tmp_path, monkeypatch, report, expected_code):
    from scripts import smoke_packaged as smoke
    from config import ApplicationSettings
    executable = tmp_path / 'Installed App' / 'pharma_khaato.exe'
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setattr(smoke, 'SMOKE_DATA', tmp_path / 'Smoke Data')
    monkeypatch.setattr(sys, 'argv', ['smoke_packaged.py', '--executable', str(executable)])
    def run(command, **kwargs):
        assert kwargs['cwd'] == str(executable.parent)
        if report is not None:
            value = {'ok':True,'version':ApplicationSettings.APP_VERSION,'check':'functional-smoke'} if report == 'valid' else report
            target = command[command.index('--smoke-report') + 1]
            from pathlib import Path
            Path(target).write_text(json.dumps(value), encoding='utf-8')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(smoke.subprocess, 'run', run)
    assert smoke.main() == expected_code


def test_build_script_imports_without_shell_pythonpath(tmp_path):
    import subprocess
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'build_release.py'
    result = subprocess.run([sys.executable, '-I', '-c',
        'import runpy,sys; runpy.run_path(sys.argv[1], run_name="build_import_check")', str(script)],
        cwd=tmp_path, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
