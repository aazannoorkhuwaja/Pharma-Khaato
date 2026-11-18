"""Keep frozen GIO from mixing its bundled GLib ABI with host native plugins."""
import os
from pathlib import Path
import sys

if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
    # PyInstaller runs this before importing Qt or any application modules.
    module_dir = Path(sys._MEIPASS) / 'gio-modules'
    if not module_dir.is_dir():
        raise RuntimeError('The installed GIO module directory is missing. Reinstall the complete application.')
    os.environ['GIO_MODULE_DIR'] = str(module_dir)
    os.environ.pop('GIO_EXTRA_MODULES', None)
