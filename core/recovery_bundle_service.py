#!/usr/bin/env python3
"""Owner-only encrypted new-host recovery bundle; never extracts over live data."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

_MAGIC = b'PKRECOVERY1\x00'
_LIMIT = 256 * 1024 * 1024
_MAX_FILES = 10000


def _cipher(passphrase, salt):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not isinstance(passphrase, str) or len(passphrase) < 16:
        raise ValueError('Use a recovery passphrase of at least 16 characters.')
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode('utf-8'))
    return AESGCM(key)


def _atomic_new_file(path, contents):
    # Exclusive creation refuses accidental replacement of an owner recovery copy.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise


def export_bundle(destination, username, password, passphrase):
    """Authenticate the current owner and package a freshly signed snapshot."""
    from core.auth_service import login_user
    from core.backup_service import backup_database
    from core.backup_trust import verify_snapshot
    from core.path_manager import PathManager
    from core.permission_service import require_permission
    # Validate before any backup creation/password work.
    if len(passphrase) < 16:
        raise ValueError('Use a recovery passphrase of at least 16 characters.')
    user = login_user(username, password)
    if not user or not require_permission(int(user[0]), 'backups.manage')[0]:
        raise PermissionError('An authorized shop owner must sign in to export recovery data.')
    ok, snapshot = backup_database('owner_recovery')
    if not ok or not verify_snapshot(snapshot):
        raise RuntimeError('A verified recovery snapshot could not be created.')
    base = Path(PathManager.get_base_data_dir())
    sources = {'data/pharmacy_db.sqlite': Path(snapshot), 'data/pharmacy_db.sqlite.hmac': Path(snapshot + '.hmac')}
    for folder in ('config', 'receipts'):
        for path in (base / folder).rglob('*'):
            if path.is_symlink():
                raise ValueError('Recovery data contains a symbolic link; review it before export.')
            if not path.is_file():
                continue
            # Interrupted restore staging is not a valid authority/configuration.
            relative = path.relative_to(base).as_posix()
            if folder == 'config' and (path.name in {'backup.json', 'restore-pending.json', 'recovery-attempts.json'}
                                      or any(part.startswith('recovery-') for part in path.relative_to(base / folder).parts[:-1])):
                continue
            sources[relative] = path
    if len(sources) > _MAX_FILES or sum(p.stat().st_size for p in sources.values()) > _LIMIT:
        raise ValueError('Recovery bundle exceeds the 256 MiB/10,000-file supported limit. Use the documented large-store recovery procedure.')
    buffer = io.BytesIO()
    manifest = {'format': 1, 'files': {}}
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, source in sorted(sources.items()):
            content = source.read_bytes()
            manifest['files'][name] = hashlib.sha256(content).hexdigest()
            archive.writestr(name, content)
        archive.writestr('manifest.json', json.dumps(manifest, sort_keys=True))
    plaintext = buffer.getvalue()
    if len(plaintext) > _LIMIT:
        raise ValueError('Recovery bundle exceeds the supported size limit.')
    salt, nonce = os.urandom(16), os.urandom(12)
    ciphertext = _cipher(passphrase, salt).encrypt(nonce, plaintext, _MAGIC)
    destination = Path(destination).expanduser().resolve()
    _atomic_new_file(destination, _MAGIC + salt + nonce + ciphertext)
    return str(destination)


def _safe_name(name):
    path = PurePosixPath(name)
    return (not path.is_absolute() and '\\' not in name and ':' not in name and
            all(part not in {'', '.', '..'} for part in name.split('/')) and
            (name == 'manifest.json' or (path.parts[0] in {'data', 'config', 'receipts'} and len(path.parts) > 1)))


def import_bundle(bundle, destination, passphrase):
    """Decrypt/validate into a new directory. Existing data is never replaced."""
    from cryptography.exceptions import InvalidTag
    from core.backup_service import _validate_sqlite_database
    from core.backup_trust import _digest
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new, nonexistent recovery directory. Existing data is never overwritten.')
    source = Path(bundle)
    if source.stat().st_size > _LIMIT + 1024:
        raise ValueError('Recovery bundle exceeds the supported size limit.')
    encoded = source.read_bytes()
    prefix = len(_MAGIC)
    if not encoded.startswith(_MAGIC) or len(encoded) < prefix + 44:
        raise ValueError('Not a supported recovery bundle.')
    try:
        plaintext = _cipher(passphrase, encoded[prefix:prefix + 16]).decrypt(
            encoded[prefix + 16:prefix + 28], encoded[prefix + 28:], _MAGIC)
    except InvalidTag as exc:
        raise ValueError('Wrong recovery passphrase or damaged bundle.') from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.pharma-recovery-', dir=destination.parent))
    try:
        with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
            members = archive.infolist()
            names = [m.filename for m in members]
            if len(members) > _MAX_FILES + 1 or len(set(names)) != len(names) or sum(m.file_size for m in members) > _LIMIT:
                raise ValueError('Invalid recovery manifest size or duplicate names.')
            if any(not _safe_name(name) for name in names):
                raise ValueError('Invalid recovery entry path.')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('format') != 1 or set(manifest.get('files', {})) != set(names) - {'manifest.json'}:
                raise ValueError('Recovery manifest does not match its files.')
            for member in members:
                if member.filename == 'manifest.json':
                    continue
                content = archive.read(member)
                if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), manifest['files'][member.filename]):
                    raise ValueError('Recovery file failed integrity verification.')
                path = (stage / member.filename).resolve()
                if not path.is_relative_to(stage.resolve()):
                    raise ValueError('Invalid recovery entry path.')
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                _atomic_new_file(path, content)
        database = stage / 'data/pharmacy_db.sqlite'
        key = (stage / 'config/recovery.key').read_bytes()
        signature = (stage / 'data/pharmacy_db.sqlite.hmac').read_text(encoding='ascii').strip()
        if len(key) != 32 or not hmac.compare_digest(signature, _digest(database, key)):
            raise ValueError('Recovery snapshot signature is invalid.')
        valid, message = _validate_sqlite_database(str(database))
        if not valid:
            raise ValueError('Recovery database was rejected: ' + message)
        connection_file = stage / 'config/counter_connection.json'
        if connection_file.exists():
            values = json.loads(connection_file.read_text(encoding='utf-8'))
            if values.get('mode') == 'host':
                # Host identities have fixed names assigned by ensure_shop_certificate.
                # Never derive a filesystem path from decrypted configuration text.
                for field, filename in (('certificate_path', 'shop-certificate.pem'),
                                        ('key_path', 'shop-private-key.pem')):
                    relative = Path('config/shop-tls') / filename
                    if not (stage / relative).is_file():
                        raise ValueError('The host TLS recovery identity is incomplete.')
                    values[field] = str(destination / relative)
            elif values.get('mode') == 'counter':
                relative = Path('config/trusted-shop.pem')
                if not (stage / relative).is_file():
                    raise ValueError('The trusted shop certificate is missing.')
                values['certificate_path'] = str(destination / relative)
            connection_file.write_text(json.dumps(values, indent=2), encoding='utf-8')
        # No startup may treat an interrupted operation as definitively absent.
        # Retain pending JSON operation identities as exported and reconcile online.
        os.rename(stage, destination)
        return str(destination)
    except (KeyError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('The recovery bundle is incomplete or invalid.') from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)

