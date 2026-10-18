#!/usr/bin/env python3
"""Verify the actual Linux archive, launchers and shop-data retention in isolation."""
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import ApplicationSettings


def run(*args, env):
    subprocess.run([str(a) for a in args], env=env, check=True, timeout=90)


def main():
    archive = ROOT / 'release' / f'Pharma-Khaato-{ApplicationSettings.APP_VERSION}-linux-x86_64.tar.gz'
    with tempfile.TemporaryDirectory(prefix='Pharma Linux Install ') as temporary:
        base = Path(temporary)
        home = base / 'Shop Owner'
        home.mkdir()
        env = os.environ.copy()
        env.update(HOME=str(home), XDG_DATA_HOME=str(home / 'Application Data'),
                   QT_QPA_PLATFORM='offscreen')
        # Exercise the real default XDG shop location, separate from app binaries.
        data = Path(env['XDG_DATA_HOME']) / 'pharma-khaato'
        env['PHARMA_KHAATO_DATA_DIR'] = str(data)
        with tarfile.open(archive) as bundle:
            bundle.extractall(base / 'download', filter='data')
        folder, = (base / 'download').iterdir()
        run('sh', folder / 'install.sh', env=env)
        executable = home / '.local/bin/pharma-khaato'
        run(sys.executable, ROOT / 'scripts/smoke_packaged.py', '--executable', executable, env=env)
        run(executable, '--self-check', '--headless', env=env)
        database = data / 'data/pharmacy_db.sqlite'
        with sqlite3.connect(database) as connection:
            connection.execute("INSERT INTO Pharmacy_Settings(setting_key,setting_value) VALUES('pharmacy_name','Linux retention check') ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value")
        digest = hashlib.sha256(database.read_bytes()).hexdigest()
        desktop = Path(env['XDG_DATA_HOME']) / 'applications/pharma-khaato.desktop'
        assert desktop.is_file()
        run('desktop-file-validate', desktop, env=env)
        # A failed copy/source validation must preserve the previous installation.
        (folder / 'app/pharma_khaato').rename(folder / 'app/temporarily-missing')
        result = subprocess.run(['sh', str(folder / 'install.sh')], env=env, timeout=30)
        assert result.returncode != 0 and executable.is_file()
        (folder / 'app/temporarily-missing').rename(folder / 'app/pharma_khaato')
        run('sh', folder / 'install.sh', env=env)
        assert hashlib.sha256(database.read_bytes()).hexdigest() == digest
        run(sys.executable, ROOT / 'scripts/smoke_packaged.py', '--executable', executable, env=env)
        run('sh', folder / 'uninstall.sh', env=env)
        assert not executable.exists() and not desktop.exists()
        assert hashlib.sha256(database.read_bytes()).hexdigest() == digest
    print('PASS: Linux archive install, installed functional check, failed-install safety, reinstall and database retention.')


if __name__ == '__main__':
    main()
