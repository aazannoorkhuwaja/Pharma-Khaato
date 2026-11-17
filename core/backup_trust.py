"""Authenticate pre-login backups using a separately protected shop key.

The key is local recovery authority, not a password supplied by the backup.
Keep an offline owner-controlled copy for disaster recovery on a new machine.
"""
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import tempfile
from core.path_manager import PathManager


def _key(create=False):
    path = Path(PathManager.get_config_dir()) / 'recovery.key'
    if create and not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(secrets.token_bytes(32))
                stream.flush()
                os.fsync(stream.fileno())
    value = path.read_bytes()
    if len(value) != 32:
        raise ValueError('The shop recovery key is invalid.')
    return value


def _digest(path, key):
    digest = hmac.new(key, digestmod=hashlib.sha256)
    with open(path, 'rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sign_snapshot(path):
    target = Path(str(path) + '.hmac')
    digest = _digest(path, _key(create=True))
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='.signature-')
    try:
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(digest)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_snapshot(path):
    try:
        tag = Path(str(path) + '.hmac').read_text(encoding='ascii').strip()
        return len(tag) == 64 and hmac.compare_digest(tag, _digest(path, _key()))
    except (OSError, ValueError, UnicodeError):
        return False
