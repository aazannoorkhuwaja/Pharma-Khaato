#!/usr/bin/env python3
"""Build a distributable Pharma-Khaato package for the current OS.

Windows runners produce a .zip that can be used directly or wrapped by
``installer.iss``. Linux runners produce a self-contained .tar.gz plus desktop
installer helpers. PyInstaller does not cross-compile, so build each target on
its native OS or use the included CI matrix.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from config import ApplicationSettings

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"
APP_DIR = DIST / "pharma_khaato"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def build_pyinstaller() -> None:
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(DIST, ignore_errors=True)
    RELEASE.mkdir(exist_ok=True)
    run(sys.executable, "-m", "PyInstaller", "pharma_khaato.spec", "--clean", "--noconfirm")
    if not APP_DIR.exists():
        raise RuntimeError(f"PyInstaller output not found: {APP_DIR}")


def package_windows(version: str) -> Path:
    out = RELEASE / f"Pharma-Khaato-{version}-windows-x64.zip"
    if out.exists():
        out.unlink()
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
    if out.exists():
        out.unlink()
    with tarfile.open(out, "w:gz") as tf:
        tf.add(stage, arcname=stage.name)
    shutil.rmtree(stage)
    return out


def main() -> int:
    build_pyinstaller()
    version = ApplicationSettings.APP_VERSION
    system = platform.system()
    if system == "Windows":
        artifact = package_windows(version)
    elif system == "Linux":
        artifact = package_linux(version)
    else:
        raise RuntimeError(f"Unsupported release target: {system}. Supported: Windows, Linux")
    print(f"Release artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
