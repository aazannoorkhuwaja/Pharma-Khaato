#!/usr/bin/env python3
"""Command-line owner recovery; the installed GUI uses the same service."""
import argparse
import getpass
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.recovery_bundle_service import export_bundle, import_bundle, _MAGIC, _cipher

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export', help='Close the app/server first; authenticate the owner and export an encrypted bundle')
    export.add_argument('--data-dir', required=True)
    export.add_argument('--output', required=True)
    export.add_argument('--username', required=True)
    recover = sub.add_parser('import', help='Recover only into a new directory; original remains unchanged')
    recover.add_argument('--bundle', required=True)
    recover.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    if args.command == 'export':
        os.environ['PHARMA_KHAATO_DATA_DIR'] = str(Path(args.data_dir).expanduser().resolve())
        os.environ['PHARMA_KHAATO_SHOP_SERVER'] = '1'
        password = getpass.getpass('Shop owner password: ')
        passphrase = getpass.getpass('New recovery passphrase (at least 16 characters): ')
        if passphrase != getpass.getpass('Repeat recovery passphrase: '):
            parser.error('Recovery passphrases do not match.')
        result = export_bundle(args.output, args.username, password, passphrase)
    else:
        # Keep any imported logger/path initialization outside an existing shop.
        with tempfile.TemporaryDirectory(prefix='pharma-import-runtime-') as runtime:
            os.environ['PHARMA_KHAATO_DATA_DIR'] = runtime
            result = import_bundle(args.bundle, args.destination, getpass.getpass('Recovery passphrase: '))
    print('Recovery operation completed:', result)
    print('Start the recovered shop only after validating host address, backup destination and reconciliation. Keep the original offline.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, PermissionError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
