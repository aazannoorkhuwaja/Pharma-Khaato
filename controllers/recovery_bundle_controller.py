"""Trusted standalone recovery entry point; never exposed to LAN callers."""
from pathlib import Path
import os

def perform_recovery(mode, source, destination, username, password, passphrase):
    """Runs only in the standalone utility, outside a running desktop session."""
    from core.recovery_bundle_service import export_bundle, import_bundle
    if mode == 'export':
        base = Path(source).expanduser().resolve()
        if not any((base / name).is_file() for name in ('data/pharmacy_db.sqlite', 'pharmacy_db.sqlite')):
            raise ValueError('Choose the existing shop data folder; no pharmacy database was found.')
        from core.path_manager import PathManager
        os.environ['PHARMA_KHAATO_DATA_DIR'] = str(base)
        os.environ['PHARMA_KHAATO_SHOP_SERVER'] = '1'
        PathManager._BASE_DATA_DIR = None
        return export_bundle(destination, username, password, passphrase)
    if mode == 'import':
        return import_bundle(source, destination, passphrase)
    raise ValueError('Choose export or import.')

