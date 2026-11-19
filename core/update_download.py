"""Stage an official release package for the native installer."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

from core.version_service import REPOSITORY, _parse_version

MAX_PACKAGE_BYTES = 512 * 1024 * 1024


def download_package(info):
    version = info['latest_version']
    tag = info['tag']
    name = info['package_name']
    if not _parse_version(version) or tag not in (version, 'v' + version):
        raise ValueError('Invalid release version.')
    if name not in {f'Pharma-Khaato-{version}-{suffix}' for suffix in
                    ('Setup-Windows-x64.exe', 'linux-amd64.deb', 'linux-x86_64.tar.gz')}:
        raise ValueError('Invalid installer name.')
    url = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
    with urllib.request.urlopen(url + '.sha256', timeout=15) as response:
        checksum = response.read(1025)
    match = re.fullmatch(rb'([0-9a-fA-F]{64})\s+\*?' + re.escape(name.encode()) + rb'\s*', checksum)
    if not match or len(checksum) > 1024:
        raise ValueError('Invalid installer checksum file.')
    directory = Path(tempfile.mkdtemp(prefix='pharma-update-'))
    target = directory / name
    try:
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(url, timeout=30) as response, target.open('xb') as dest:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > MAX_PACKAGE_BYTES:
                    raise ValueError('Installer exceeds the download limit.')
                dest.write(block)
                digest.update(block)
        if not total or digest.hexdigest() != match[1].decode().lower():
            raise ValueError('Installer checksum did not match.')
        if name.endswith('.exe'):
            powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command',
                            "if ((Get-AuthenticodeSignature -LiteralPath $env:PHARMA_UPDATE_FILE).Status -ne 'Valid') {exit 1}"],
                           env=dict(os.environ, PHARMA_UPDATE_FILE=str(target)), check=True, timeout=45)
        return str(target)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
