#!/usr/bin/env python3
"""Fail closed on missing/mismatched native assets before creating a draft release."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def prepare(directory, version, revision):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('A numeric major.minor.patch release version is required.')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('An exact Git commit SHA is required.')
    names = [f'Pharma-Khaato-{version}-Setup-Windows-x64.exe',
             f'Pharma-Khaato-{version}-linux-x86_64.tar.gz',
             f'Pharma-Khaato-{version}-linux-amd64.deb']
    assets = []
    for name in names:
        path = directory / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing or empty release asset: {name}')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        checksum = path.with_name(name + '.sha256').read_text(encoding='utf-8').strip()
        if checksum != f'{digest}  {name}':
            raise ValueError(f'Checksum mismatch: {name}')
        assets.append({'name': name, 'sha256': digest, 'bytes': path.stat().st_size})
    (directory / 'SHA256SUMS').write_text(''.join(f"{a['sha256']}  {a['name']}\n" for a in assets), encoding='utf-8')
    (directory / 'release.json').write_text(json.dumps({
        'version': version, 'revision': revision, 'assets': assets,
        'targets': ['Windows 10 1809+/11 x64', 'Ubuntu 22.04/24.04 x86_64'],
    }, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    prepare(args.directory, args.version, args.revision)


if __name__ == '__main__':
    main()
