"""Durable workstation intentions for drawer operations interrupted by restart."""
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid
from core.path_manager import PathManager

_LOCK = threading.RLock()


def _path(employee_id, domain='cash'):
    if domain not in {'cash','stock','supplier'}:
        raise ValueError('Unknown pending operation type.')
    return Path(PathManager.get_config_dir()) / f'pending-{domain}-{int(employee_id)}.json'


def pending(employee_id, domain='cash'):
    with _LOCK:
        path = _path(employee_id, domain)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding='utf-8'))
        if int(value['employee_id']) != int(employee_id):
            raise ValueError('The pending cash entry belongs to another staff member.')
        return value


def perform(employee_id, kind, payload, callback, domain='cash'):
    with _LOCK:
        path = _path(employee_id, domain)
        entry = pending(employee_id, domain)
        if entry is not None and (entry['kind'] != kind or entry['payload'] != payload):
            raise ValueError('Confirm the pending cash entry before recording a different entry.')
        if entry is None:
            entry = {'employee_id':int(employee_id),'kind':kind,'payload':payload,'operation_id':uuid.uuid4().hex}
            fd, temporary = tempfile.mkstemp(prefix='.cash-', dir=path.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as stream:
                    json.dump(entry,stream,allow_nan=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary,path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        # Transport exceptions preserve the exact intent; an acknowledged
        # success/rejection is definitive and can safely release the editor.
        result = callback(entry['operation_id'])
        if isinstance(result,(tuple,list)) and result and isinstance(result[0],bool):
            path.unlink(missing_ok=True)
        return result
