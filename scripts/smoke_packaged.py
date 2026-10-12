#!/usr/bin/env python3
"""Smoke-test the native PyInstaller build without opening an interactive UI."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "dist" / "pharma_khaato"
SMOKE_DATA = ROOT / ".release-smoke-data"


def executable_path() -> Path:
    system = platform.system()
    if system == "Windows":
        return APP_DIR / "pharma_khaato.exe"
    if system == "Linux":
        return APP_DIR / "pharma_khaato"
    raise RuntimeError(f"Unsupported smoke-test platform: {system}")


def main() -> int:
    exe = executable_path()
    if not exe.exists():
        print(f"Packaged executable not found: {exe}", file=sys.stderr)
        return 2

    shutil.rmtree(SMOKE_DATA, ignore_errors=True)
    env = os.environ.copy()
    env["PHARMA_KHAATO_DATA_DIR"] = str(SMOKE_DATA)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONUTF8"] = "1"

    try:
        completed = subprocess.run(
            [str(exe), "--self-check", "--headless"],
            cwd=str(APP_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("Packaged self-check timed out after 60 seconds.", file=sys.stderr)
        return 3

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    if completed.returncode != 0:
        print(f"Packaged self-check failed with exit code {completed.returncode}.", file=sys.stderr)
        return completed.returncode

    print(f"Packaged executable smoke test passed: {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
