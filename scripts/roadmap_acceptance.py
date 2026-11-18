"""Create/validate human-reviewable release acceptance evidence, without deploying.

A template is intentionally blocked. Every gate needs real evidence for the
exact revision/artifact. This validates completeness, not the truth of claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

GATES = (
    'financial_reconciliation', 'medicine_policy', 'authorization', 'lan_faults_and_load',
    'upgrade_legacy_data', 'crash_and_restore', 'windows_install_upgrade_uninstall',
    'linux_install_upgrade_uninstall', 'signed_windows_artifacts', 'dependency_advisories',
    'license_review', 'keyboard_and_accessibility', 'windows_dpi', 'printer', 'scanner',
    'operator_pilot', 'support_and_rpo_rto', 'owner_release_approval',
)


def template(revision):
    return {'schema':1, 'revision':revision, 'artifacts':[], 'gates':{
        gate:{'status':'not_run','reviewer':'','evidence':[],'notes':''} for gate in GATES}}


def validate(document, base):
    failures=[]
    if not re.fullmatch(r'[0-9a-f]{40}', str(document.get('revision',''))):
        failures.append('An exact 40-character source revision is required.')
    if document.get('schema') != 1:
        failures.append('Unsupported acceptance schema.')
    if not document.get('artifacts'):
        failures.append('No release artifacts were identified.')
    for artifact in document.get('artifacts',[]):
        if not artifact.get('name') or not re.fullmatch(r'[0-9a-f]{64}',str(artifact.get('sha256',''))):
            failures.append('Every artifact requires its name and SHA-256.')
    for gate in GATES:
        row=document.get('gates',{}).get(gate,{})
        if row.get('status')!='passed' or not str(row.get('reviewer','')).strip() or not row.get('evidence'):
            failures.append(f'{gate}: needs passed status, named reviewer and evidence.')
            continue
        for evidence in row['evidence']:
            path=(base / str(evidence.get('path',''))).resolve()
            if not path.is_relative_to(base.resolve()) or not path.is_file():
                failures.append(f'{gate}: evidence must be a file inside the acceptance directory.')
                continue
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if evidence.get('sha256') != digest:
                failures.append(f'{gate}: evidence checksum mismatch.')
    return failures


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--create',action='store_true')
    parser.add_argument('--revision',default='')
    args=parser.parse_args()
    if args.create:
        with args.manifest.open('x',encoding='utf-8') as stream:
            json.dump(template(args.revision),stream,indent=2)
        return 0
    errors=validate(json.loads(args.manifest.read_text(encoding='utf-8')), args.manifest.parent)
    for error in errors:
        print(error)
    if not errors:
        print('Evidence manifest is complete. Human review remains required; nothing was published.')
    return 1 if errors else 0


if __name__=='__main__':
    raise SystemExit(main())
