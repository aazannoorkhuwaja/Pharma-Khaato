#!/usr/bin/env python3
"""Install/reinstall/remove the real .deb on an isolated disposable CI runner."""
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import ApplicationSettings


def main():
    package = ROOT / 'release' / f'Pharma-Khaato-{ApplicationSettings.APP_VERSION}-linux-amd64.deb'
    def run(*args, env=None):
        subprocess.run([str(a) for a in args], env=env, check=True, timeout=120)
    with tempfile.TemporaryDirectory(prefix='Pharma Debian Check ') as temporary:
        data = Path(temporary) / 'Shop Data'
        env = os.environ.copy()
        env.update(PHARMA_KHAATO_DATA_DIR=str(data), QT_QPA_PLATFORM='offscreen')
        run('sudo', 'dpkg', '-i', package)
        try:
            run('desktop-file-validate', '/usr/share/applications/pharma-khaato.desktop')
            run(sys.executable, ROOT / 'scripts/smoke_packaged.py', '--executable', '/usr/bin/pharma-khaato', env=env)
            run('/usr/bin/pharma-khaato', '--self-check', '--headless', env=env)
            database = data / 'data/pharmacy_db.sqlite'
            with sqlite3.connect(database) as connection:
                connection.execute("INSERT INTO Pharmacy_Settings(setting_key,setting_value) VALUES('pharmacy_name','Debian retention check') ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value")
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            run('sudo', 'dpkg', '-i', package)
            assert hashlib.sha256(database.read_bytes()).hexdigest() == before
            # Override offscreen to exercise the bundled xcb plugin under Xvfb.
            run('xvfb-run', '-a', '/usr/bin/pharma-khaato', '--functional-smoke', '--platform', 'xcb', env=env)
        finally:
            run('sudo', 'dpkg', '--remove', 'pharma-khaato')
        assert not Path('/opt/pharma-khaato/pharma_khaato').exists()
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    print('PASS: Debian install, X11 desktop runtime, reinstall and shop records retained after removal.')


if __name__ == '__main__':
    main()
