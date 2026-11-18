"""Launch the current source against a local practice shop."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--new', action='store_true', help='Create and select a fresh practice shop')
    parser.add_argument('--self-check', action='store_true', help='Check the selected practice shop and exit')
    args = parser.parse_args()
    if os.name == 'nt':
        parent = Path(os.environ.get('LOCALAPPDATA') or Path.home())
    else:
        parent = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    root = parent / 'Pharma-Khaato-Practice'
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    selected = root / 'current'
    if args.new or not selected.exists():
        shop = uuid4().hex
        (root / shop).mkdir(mode=0o700)
        temp = root / (shop + '.tmp')
        temp.write_text(shop, encoding='ascii')
        temp.replace(selected)
    shop = selected.read_text(encoding='ascii')
    if len(shop) != 32 or any(ch not in '0123456789abcdef' for ch in shop):
        parser.error('Invalid practice shop selection. Use --new to create another.')
    env = os.environ.copy()
    env.update(PHARMA_KHAATO_DATA_DIR=str((root / shop).resolve()), PHARMA_KHAATO_SHOP_SERVER='1',
               PHARMA_KHAATO_BACKUP_DIR='', PHARMA_KHAATO_SERVER_URL='', PHARMA_KHAATO_SERVER_CERT='',
               PHARMA_KHAATO_PRACTICE='1', PYTHON_DOTENV_DISABLED='1')
    source = Path(__file__).resolve().parent
    command = [sys.executable, str(source / 'main.py')]
    if args.self_check:
        command.extend(['--self-check', '--headless'])
    return subprocess.call(command, env=env, cwd=source)


if __name__ == '__main__':
    raise SystemExit(main())
