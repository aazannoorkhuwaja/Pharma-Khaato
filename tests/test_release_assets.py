"""Publication requires complete verified native assets, never a partial release."""
import hashlib
import json

import pytest
from scripts.prepare_release import prepare


def assets(directory):
    names = ['Pharma-Khaato-2.4.0-Setup-Windows-x64.exe',
             'Pharma-Khaato-2.4.0-linux-x86_64.tar.gz',
             'Pharma-Khaato-2.4.0-linux-amd64.deb']
    for name in names:
        content = ('test asset: ' + name).encode()
        (directory / name).write_bytes(content)
        (directory / (name + '.sha256')).write_text(f'{hashlib.sha256(content).hexdigest()}  {name}\n')
    return names


def test_manifest_identifies_both_platforms_and_exact_commit(tmp_path):
    names = assets(tmp_path)
    prepare(tmp_path, '2.4.0', 'a' * 40)
    manifest = json.loads((tmp_path / 'release.json').read_text())
    assert manifest['revision'] == 'a' * 40
    assert [a['name'] for a in manifest['assets']] == names
    assert len((tmp_path / 'SHA256SUMS').read_text().splitlines()) == 3


@pytest.mark.parametrize('problem', ['missing', 'empty', 'tampered', 'wrong-sidecar'])
def test_partial_or_tampered_release_cannot_be_prepared(tmp_path, problem):
    name = assets(tmp_path)[-1]
    path = tmp_path / name
    if problem == 'missing':
        path.unlink()
    elif problem == 'empty':
        path.write_bytes(b'')
    elif problem == 'tampered':
        path.write_bytes(b'changed after checksum')
    else:
        (tmp_path / (name + '.sha256')).write_text('not the published checksum')
    with pytest.raises(ValueError):
        prepare(tmp_path, '2.4.0', 'a' * 40)
    assert not (tmp_path / 'release.json').exists()


@pytest.mark.parametrize('version,revision', [('2.4.0-beta', 'a' * 40), ('2.4.0', 'main')])
def test_release_identity_must_be_exact(tmp_path, version, revision):
    with pytest.raises(ValueError):
        prepare(tmp_path, version, revision)
