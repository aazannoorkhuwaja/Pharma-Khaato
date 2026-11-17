"""Process-lifetime ownership of a local shop store, shared by GUI and CLI.

The OS releases locks after process exit/crash. Never delete the lock file:
removing it would allow a second process to lock a different inode.
"""
import atexit
import os
from pathlib import Path
import threading

_LOCK = threading.RLock()
_HANDLES = {}


def acquire_store(path):
    target = str(Path(path).resolve())
    with _LOCK:
        existing = _HANDLES.get(target)
        if existing and existing[0] == os.getpid():
            return
        if existing:
            existing[1].close()  # inherited handle; child must obtain its own lock
            del _HANDLES[target]
        lock_path = Path(target).parent / '.shop-owner.lock'
        lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        handle = os.fdopen(fd, 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            handle.close()
            raise RuntimeError('This shop data is already open in another process. Close that application or shop server first.') from exc
        _HANDLES[target] = (os.getpid(), handle)


@atexit.register
def _release_at_exit():
    for _, handle in _HANDLES.values():
        handle.close()
    _HANDLES.clear()
