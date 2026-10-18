"""Optional release metadata checks. No shop records are read or transmitted."""
from __future__ import annotations

import json
import platform
import re
import time
import urllib.request
from pathlib import Path

from config import ApplicationSettings
from core.path_manager import PathManager

REPOSITORY = 'aazannoorkhuwaja/Pharma-Khaato'
VERSION_CHECK_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
CHECK_INTERVAL = 24 * 60 * 60
MAX_RESPONSE_BYTES = 1_000_000


def _parse_version(tag):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', str(tag))
    return tuple(map(int, match.groups())) if match else None


def _state_path():
    return Path(PathManager.get_config_dir()) / 'update-check.json'


def _last_success():
    try:
        return float(json.loads(_state_path().read_text(encoding='utf-8'))['last_success'])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def _save_success():
    try:
        path = _state_path()
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'last_success': time.time()}), encoding='utf-8')
        temporary.replace(path)
    except OSError:
        pass  # Optional update preferences must never prevent shop work.


def _release_info(data):
    if not isinstance(data, dict) or data.get('draft') or data.get('prerelease'):
        return None
    latest = _parse_version(data.get('tag_name'))
    current = _parse_version(ApplicationSettings.APP_VERSION)
    if latest is None or current is None or latest <= current:
        return None
    version = '.'.join(map(str, latest))
    system = platform.system()
    if system == 'Windows':
        expected = f'Pharma-Khaato-{version}-Setup-Windows-x64.exe'
    elif system == 'Linux':
        expected = f'Pharma-Khaato-{version}-linux-x86_64.tar.gz'
    else:
        return None
    assets = data.get('assets')
    if not isinstance(assets, list):
        return None
    names = {asset.get('name') for asset in assets if isinstance(asset, dict)}
    if not {expected, expected + '.sha256'} <= names:
        return None  # Do not offer a release before its platform package is ready.
    tag = str(data['tag_name'])
    return {'has_update': True, 'current_version': ApplicationSettings.APP_VERSION,
            'latest_version': version, 'release_notes': str(data.get('body') or 'See the release page for the changes in this version.')[:20000],
            'download_url': f'https://github.com/{REPOSITORY}/releases/tag/{tag}'}


def check_update_status(timeout=3.0, *, force=False):
    """Run in a worker. Offline retries are cheap; successful reads are daily."""
    elapsed = time.time() - _last_success()
    if not force and 0 <= elapsed < CHECK_INTERVAL:
        return {'status': 'deferred'}
    try:
        request = urllib.request.Request(VERSION_CHECK_URL, headers={
            'User-Agent': f'Pharma-Khaato/{ApplicationSettings.APP_VERSION}',
            'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('Release response too large')
        data = json.loads(raw.decode('utf-8'))
        if not isinstance(data, dict) or _parse_version(data.get('tag_name')) is None:
            raise ValueError('Release response is invalid')
        info = _release_info(data)
        _save_success()
        if info:
            return {'status': 'available', 'update': info}
        if _parse_version(data['tag_name']) > _parse_version(ApplicationSettings.APP_VERSION):
            return {'status': 'unavailable'}
        return {'status': 'current'}
    except Exception:
        return {'status': 'offline'}


def check_for_updates(timeout=3.0):
    """Compatibility entry point for callers needing only update information."""
    return check_update_status(timeout).get('update')
