"""Generate runtime dependency versions, license texts and hashes for packaging.

Run in the clean release build environment. This inventories installed runtime
packages, not dev tooling; native artifact hashes are an optional second pass.
"""
from __future__ import annotations
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def runtime_names(requirements=ROOT / 'requirements.txt'):
    result = []
    for line in requirements.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate():
            result.append(requirement.name)
    return result


def dependency_closure(names, distribution=metadata.distribution):
    found = {}
    pending = list(names)
    while pending:
        name = canonicalize_name(pending.pop())
        if name in found:
            continue
        dist = distribution(name)  # Missing runtime packages deliberately fail the build.
        found[name] = dist
        for raw in dist.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
                pending.append(requirement.name)
    return found


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def generate(output, *, artifact_dir=None):
    output.mkdir(parents=True, exist_ok=True)
    for raw in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        required = Requirement(raw)
        if required.marker is not None and not required.marker.evaluate():
            continue
        installed = metadata.version(required.name)
        if required.specifier and installed not in required.specifier:
            raise ValueError(f'Release environment mismatch: {required.name} {installed}; expected {required.specifier}')
    packages = []
    notices = ['# Third-party runtime components', '',
               'Generated from the installed runtime dependency closure. License texts are included below.',
               'This inventory does not replace a review of distribution obligations for the shipped binaries.', '']
    for name, dist in sorted(dependency_closure(runtime_names()).items()):
        expression = dist.metadata.get('License-Expression') or dist.metadata.get('License') or ''
        texts = []
        sources = []
        for entry in dist.files or []:
            if not re.search(r'(^|[/\\])(licen[cs]e[^/\\]*|copying[^/\\]*|notice[^/\\]*)([/\\]|$)', str(entry), re.I):
                continue
            source = Path(dist.locate_file(entry))
            if not source.is_file():
                continue
            sources.append(source)
        if name in {'pyside6-essentials', 'shiboken6'}:
            # The wheels declare these alternatives but omit their full texts.
            license_names = {'LGPL-3.0-only': 'LGPL-3', 'GPL-2.0-only': 'GPL-2', 'GPL-3.0-only': 'GPL-3'}
            declared = set(expression.split(' OR '))
            if declared != set(license_names):
                raise ValueError(f'Review the changed Qt license declaration for {name}: {expression}')
            sources.extend(ROOT / 'packaging' / 'licenses' / filename for filename in license_names.values())
        for source in sources:
            digest = file_hash(source)
            relative = Path('licenses') / name / (digest[:12] + '-' + source.name)
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            texts.append({'path':relative.as_posix(), 'sha256':digest})
        if not expression.strip() and not texts:
            raise ValueError(f'No license metadata/text found for runtime dependency {name}')
        packages.append({'name':name, 'version':dist.version, 'license':expression,
                         'license_files':texts, 'requires':dist.requires or []})
        notices += [f'## {name} {dist.version}', '', expression or 'See bundled license text.', '']
        notices += [f'- [{row["path"]}]({row["path"]})' for row in texts]
        notices.append('')
    manifest = {'schema':1, 'python':sys.version.split()[0],
                'scope':'Installed runtime dependency closure; native artifact inventory is separate.', 'packages':packages}
    (output / 'runtime-dependencies.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    (output / 'THIRD_PARTY_NOTICES.md').write_text('\n'.join(notices), encoding='utf-8')
    if artifact_dir:
        files = [{'path':p.relative_to(artifact_dir).as_posix(),'size':p.stat().st_size,'sha256':file_hash(p)}
                 for p in sorted(artifact_dir.rglob('*')) if p.is_file() and not p.is_symlink()]
        (output / 'artifact-files.json').write_text(json.dumps({'schema':1,'files':files},indent=2)+'\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artifact-dir', type=Path)
    args = parser.parse_args()
    generate(args.output, artifact_dir=args.artifact_dir)
