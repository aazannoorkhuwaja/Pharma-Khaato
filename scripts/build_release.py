#!/usr/bin/env python3
"""Build a distributable Pharma-Khaato package for the current OS.

Windows runners produce a .zip that can be used directly or wrapped by
``installer.iss``. Linux runners produce a self-contained .tar.gz plus desktop
installer helpers. Every artifact receives a SHA-256 sidecar so a downloaded
release can be verified before installation.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import ApplicationSettings
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"
APP_DIR = DIST / "pharma_khaato"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def build_pyinstaller() -> None:
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(DIST, ignore_errors=True)
    # Never mix artifacts from different commits or platforms.
    shutil.rmtree(RELEASE, ignore_errors=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    run(sys.executable, "-m", "PyInstaller", "pharma_khaato.spec", "--clean", "--noconfirm")
    if not APP_DIR.exists():
        raise RuntimeError(f"PyInstaller output not found: {APP_DIR}")


def package_windows(version: str) -> Path:
    out = RELEASE / f"Pharma-Khaato-{version}-windows-x64.zip"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in APP_DIR.rglob("*"):
            if file.is_file():
                zf.write(file, Path("Pharma-Khaato") / file.relative_to(APP_DIR))
    return out


def package_linux(version: str) -> Path:
    stage = RELEASE / f"Pharma-Khaato-{version}-linux-x86_64"
    shutil.rmtree(stage, ignore_errors=True)
    app_stage = stage / "app"
    shutil.copytree(APP_DIR, app_stage)
    shutil.copy2(ROOT / "packaging" / "linux" / "pharma-khaato.desktop", stage)
    shutil.copy2(ROOT / "packaging" / "linux" / "install.sh", stage)
    shutil.copy2(ROOT / "packaging" / "linux" / "uninstall.sh", stage)
    for script in (stage / "install.sh", stage / "uninstall.sh", app_stage / "pharma_khaato"):
        if script.exists():
            script.chmod(script.stat().st_mode | 0o111)

    out = RELEASE / f"Pharma-Khaato-{version}-linux-x86_64.tar.gz"
    with tarfile.open(out, "w:gz") as tf:
        tf.add(stage, arcname=stage.name)
    shutil.rmtree(stage)
    return out


def write_sha256(artifact: Path) -> Path:
    digest = hashlib.sha256()
    with artifact.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = artifact.with_name(artifact.name + ".sha256")
    checksum.write_text(f"{digest.hexdigest()}  {artifact.name}\n", encoding="utf-8")
    return checksum


def main() -> int:
    build_pyinstaller()
    run(sys.executable, "scripts/smoke_packaged.py")
    version = ApplicationSettings.APP_VERSION
    system = platform.system()
    if system == "Windows":
        artifact = package_windows(version)
    elif system == "Linux":
        artifact = package_linux(version)
    else:
        raise RuntimeError(f"Unsupported release target: {system}. Supported: Windows, Linux")

    checksum = write_sha256(artifact)
    if not artifact.exists() or artifact.stat().st_size <= 0:
        raise RuntimeError(f"Release artifact is empty: {artifact}")
    if not checksum.exists():
        raise RuntimeError("Release checksum was not created.")

    print(f"Release artifact: {artifact}")
    print(f"SHA-256 file:    {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
