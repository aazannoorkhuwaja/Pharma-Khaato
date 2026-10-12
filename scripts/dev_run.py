"""
Developer/demo launcher for Pharma-Khaato.

One command bootstraps a private .venv when needed, installs dependencies when
requirements change, and launches either the normal application or a completely
isolated resettable demo without touching system Python.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP_FILE = VENV_DIR / ".pharma_requirements.sha256"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _requirements_digest() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def ensure_environment() -> Path:
    py = _venv_python()
    if not py.exists():
        print("[Pharma-Khaato] Creating local .venv...")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)

    digest = _requirements_digest()
    installed_digest = STAMP_FILE.read_text(encoding="utf-8").strip() if STAMP_FILE.exists() else ""

    if digest != installed_digest:
        print("[Pharma-Khaato] Installing/updating dependencies...")
        _run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
        _run([str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        STAMP_FILE.write_text(digest, encoding="utf-8")

    return py


def _launch_command(py: Path, args: list[str]) -> list[str]:
    if "--demo" in args or "--demo-keep" in args or "--demo-check" in args:
        demo_args = []
        if "--demo-keep" in args:
            demo_args.append("--keep")
        if "--demo-check" in args:
            demo_args.append("--no-launch")
        # Other main.py flags are intentionally not mixed into demo_mode.
        return [str(py), str(ROOT / "scripts" / "demo_mode.py"), *demo_args]
    return [str(py), str(ROOT / "main.py"), *args]


def main() -> int:
    try:
        py = ensure_environment()
        return subprocess.call(_launch_command(py, sys.argv[1:]), cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        print(f"[Pharma-Khaato] Setup failed with exit code {exc.returncode}.", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"[Pharma-Khaato] Could not start the development environment: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
