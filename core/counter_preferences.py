"""Workstation-only appearance/printing preferences, independent of shop data."""
import json
import os
import tempfile
import threading
from pathlib import Path
from core.path_manager import PathManager

KEYS = {'theme_mode', 'font_scale', 'preferred_printer', 'receipt_auto_print', 'printer_template', 'automatic_update_checks'}
_LOCK = threading.RLock()


def read():
    path = Path(PathManager.get_config_dir()) / 'counter_preferences.json'
    if not path.exists():
        return {}
    with _LOCK:
        return json.loads(path.read_text(encoding='utf-8'))


def update(values):
    if not set(values) <= KEYS:
        raise ValueError('Unknown workstation preference.')
    with _LOCK:
        merged = read()
        merged.update(values)
        directory = Path(PathManager.get_config_dir())
        fd, temporary = tempfile.mkstemp(prefix='.preferences-', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(merged, stream, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, directory/'counter_preferences.json')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return True
