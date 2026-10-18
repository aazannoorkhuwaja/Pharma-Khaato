#!/usr/bin/env python3
"""Smoke-test the native PyInstaller build without opening an interactive UI."""

from __future__ import annotations

import os
import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
APP_DIR = ROOT / "dist" / "pharma_khaato"
SMOKE_DATA = ROOT / ".release-smoke-data"


def executable_path() -> Path:
    system = platform.system()
    if system == "Windows":
        return APP_DIR / "pharma_khaato.exe"
    if system == "Linux":
        return APP_DIR / "pharma_khaato"
    raise RuntimeError(f"Unsupported smoke-test platform: {system}")


def show_failure_details(report_path):
    """The GUI executable has no console on Windows; read explicit diagnostics."""
    progress = SMOKE_DATA / 'progress.jsonl'
    if progress.exists():
        print('Completed stages:', file=sys.stderr)
        print(progress.read_text(encoding='utf-8')[-8000:], file=sys.stderr)
    if report_path.exists():
        print('Functional result:', file=sys.stderr)
        print(report_path.read_text(encoding='utf-8')[-16000:], file=sys.stderr)
    log = SMOKE_DATA / 'logs' / 'app.log'
    if log.exists():
        print('Functional check log:', file=sys.stderr)
        print(log.read_text(encoding='utf-8', errors='replace')[-16000:], file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, help="Verify an installed executable instead of dist")
    args = parser.parse_args()
    exe = (args.executable or executable_path()).resolve()
    if not exe.exists():
        print(f"Packaged executable not found: {exe}", file=sys.stderr)
        return 2

    shutil.rmtree(SMOKE_DATA, ignore_errors=True)
    SMOKE_DATA.mkdir(parents=True, exist_ok=True)
    report_path = SMOKE_DATA / "functional-result.json"
    env = os.environ.copy()
    env["PHARMA_KHAATO_DATA_DIR"] = str(SMOKE_DATA)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONUTF8"] = "1"
    env["PHARMA_KHAATO_SMOKE_PROGRESS"] = str(SMOKE_DATA / "progress.jsonl")

    try:
        completed = subprocess.run(
            [str(exe), "--functional-smoke", "--headless", "--smoke-report", str(report_path)],
            cwd=str(exe.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        show_failure_details(report_path)
        print("Packaged functional check timed out after 60 seconds.", file=sys.stderr)
        return 3

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    if completed.returncode != 0:
        show_failure_details(report_path)
        print(f"Packaged functional check failed with exit code {completed.returncode}.", file=sys.stderr)
        return completed.returncode

    from config import ApplicationSettings
    expected = {"ok": True, "version": ApplicationSettings.APP_VERSION, "check": "functional-smoke"}
    if not report_path.exists() or json.loads(report_path.read_text(encoding="utf-8")) != expected:
        print("Functional check did not produce the expected success report.", file=sys.stderr)
        return 4
    print(f"Packaged executable smoke test passed: {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
