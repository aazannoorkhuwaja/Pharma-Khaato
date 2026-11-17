"""Release gates must reject incomplete or tampered acceptance evidence."""
import hashlib
from pathlib import Path
from scripts.roadmap_acceptance import GATES, template, validate


def test_default_release_manifest_is_blocked(tmp_path):
    assert validate(template('a'*40),tmp_path)


def test_evidence_checksums_and_path_boundaries(tmp_path):
    evidence=tmp_path/'check.txt';evidence.write_text('fixture proof')
    document=template('a'*40)
    document['artifacts']=[{'name':'fixture.zip','sha256':'b'*64}]
    for gate in GATES:
        document['gates'][gate]={'status':'passed','reviewer':'Test fixture reviewer',
                                'evidence':[{'path':'check.txt','sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}]}
    assert not validate(document,tmp_path)
    evidence.write_text('tampered')
    assert any('checksum mismatch' in error for error in validate(document,tmp_path))
    document['gates'][GATES[0]]['evidence'][0]['path']='../outside.txt'
    assert any('inside the acceptance directory' in error for error in validate(document,tmp_path))


def test_installer_carries_actual_runtime_notices():
    source=(Path(__file__).resolve().parents[1]/'pharma_khaato.spec').read_text()
    assert 'release_inventory.py' in source
    assert 'runtime-notices' in source
    assert "'third-party'" in source
