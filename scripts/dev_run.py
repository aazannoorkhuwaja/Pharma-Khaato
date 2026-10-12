"""
Developer Helper Launcher — Pharma-Khaato
Auto-detects virtual environments (proj, venv, .venv) for local CLI development.
"""

import os
import sys
import subprocess
import platform

IS_WINDOWS = platform.system() == "Windows"

def find_venv_python():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = []
    if IS_WINDOWS:
        for name in ("venv", "proj", ".venv", "env"):
            candidates.append(os.path.join(base, name, "Scripts", "python.exe"))
    else:
        for name in ("venv", "proj", ".venv", "env"):
            candidates.append(os.path.join(base, name, "bin", "python3"))
            candidates.append(os.path.join(base, name, "bin", "python"))

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None

def main():
    venv_py = find_venv_python()
    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    if venv_py and os.path.abspath(sys.executable) != os.path.abspath(venv_py):
        print(f"Developer launcher using virtual environment: {venv_py}")
        sys.exit(subprocess.call([venv_py, main_py] + sys.argv[1:]))
    else:
        sys.exit(subprocess.call([sys.executable, main_py] + sys.argv[1:]))

if __name__ == "__main__":
    main()
