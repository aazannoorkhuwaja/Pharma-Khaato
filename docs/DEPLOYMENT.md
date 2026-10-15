# Deployment & Packaging Guide

## Supported Targets

- Windows 10/11 x64
- Mainstream x86_64 Linux distributions with a compatible glibc/desktop environment
- Python source development on Python 3.11+

PyInstaller is a native packager, not a cross-compiler. Build the Windows package on Windows and the Linux package on Linux. The included GitHub Actions workflow does both automatically.

## One-file UI acceptance launcher

For reviewers who only want to exercise the GUI, use `PharmaKhaato-v2.3.1-Universal-Test.py`. The same file runs on Windows and Linux with Python 3.10+. It contains the application payload, creates a version-isolated virtual environment, installs `requirements.txt` on first launch, stores test data separately, and then starts the desktop application.

```powershell
# Windows
py PharmaKhaato-v2.3.1-Universal-Test.py
```

```bash
# Linux
python3 PharmaKhaato-v2.3.1-Universal-Test.py
```

First launch requires internet access to download the native PySide6 wheel. Subsequent launches reuse that runtime. `--reset-data` resets only the launcher's isolated business data; `--reinstall-runtime` rebuilds only its private virtual environment.

A single native Windows/Linux executable is not technically portable because Qt/PyInstaller bundles OS-specific binaries; production builds therefore remain native per target OS.

## Run From Source

```bash
python -m pip install -r requirements.txt
python main.py
```

For headless verification:

```bash
python main.py --headless
```

## Automated Native Release Build

```bash
python scripts/build_release.py
```

Outputs are written to `release/`:

- Windows: `Pharma-Khaato-<version>-windows-x64.zip`
- Linux: `Pharma-Khaato-<version>-linux-x86_64.tar.gz`

The workflow `.github/workflows/release-build.yml` runs tests and creates both native artifacts whenever a `v*` tag is pushed, or when run manually.

## Windows Installer

1. Install Python dependencies including PyInstaller.
2. Install Inno Setup 6 and make `iscc.exe` available on `PATH`.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/build-installer.ps1
```

The script first creates the portable Windows release. If Inno Setup is available it also compiles `installer.iss` into `dist_installer/PharmaKhaato_Setup_v<version>.exe`.

## Linux Install

Extract the generated tarball and run:

```bash
./install.sh
```

This installs application binaries into the user's XDG data area, creates a `~/.local/bin/pharma-khaato` launcher, and adds a desktop-menu entry. Root access is not required.

To remove the application binaries while preserving business data/backups:

```bash
./uninstall.sh
```

## Data Safety

Application data is never written into Program Files or the extracted application directory. Backups are created using SQLite's online backup API. Before distributing a release, smoke-test the packaged application on a clean target machine.

## Release Checklist

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
python scripts/build_release.py
```

Then verify login, POS checkout, inventory, khatoo, reporting, backup/restore, theme switching, and clean shutdown on each target OS.
