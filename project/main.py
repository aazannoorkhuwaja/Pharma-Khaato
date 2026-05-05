"""
Pharma-Khaato — Entry point
Run this file to start the app:

  Windows:   double-click main.py  OR  python main.py
  Linux/Mac: python3 main.py       OR  ./main.py
"""

import os
import sys
import subprocess
import platform

IS_WINDOWS = platform.system() == "Windows"


def _find_venv_python():
    """
    Look for a virtual-environment Python in common locations
    relative to this script's folder.
    Returns the path string, or None if not found.
    """
    base = os.path.dirname(os.path.abspath(__file__))

    candidates = []
    if IS_WINDOWS:
        # Windows venv layouts
        for name in ("venv", "proj", ".venv", "env"):
            candidates.append(os.path.join(base, name, "Scripts", "python.exe"))
    else:
        # Linux / macOS venv layouts
        for name in ("venv", "proj", ".venv", "env"):
            candidates.append(os.path.join(base, name, "bin", "python3"))
            candidates.append(os.path.join(base, name, "bin", "python"))

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def smart_launch():
    """
    If a virtual environment exists and we are NOT already running
    from it, re-launch this script using the venv Python.
    This means laymen can just double-click main.py and the app
    will automatically use the correct environment.
    """
    venv_python = _find_venv_python()
    if venv_python and os.path.abspath(sys.executable) != os.path.abspath(venv_python):
        print(f"Switching to virtual environment: {venv_python}")
        ret = subprocess.call([venv_python] + sys.argv)
        sys.exit(ret)


def check_tkinter():
    """Warn clearly if tkinter is missing (common on minimal Linux installs)."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("tkinter is not installed.")
        if not IS_WINDOWS:
            print("   Fix (Ubuntu/Debian):  sudo apt install python3-tk")
            print("   Fix (Fedora/CentOS):  sudo dnf install python3-tkinter")
        else:
            print("   Reinstall Python from https://python.org and tick 'tcl/tk' option.")
        sys.exit(1)


if __name__ == "__main__":
    smart_launch()      # switch to venv if needed
    check_tkinter()     # friendly error if tkinter missing

    from salesman_app import SalesmanApp
    import tkinter as tk

    root = tk.Tk()
    app = SalesmanApp(root)
    root.mainloop()
