# Build and install Pharma Khaato

For normal use, install the Windows Setup or Linux package from [Releases](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases). Python and Git are not needed on the shop computer. Until an official release is published, the owner can download test installers from the [build workflow](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/workflows/release-build.yml).

## Native builds

Build Windows on Windows and Linux on Linux; PyInstaller does not cross-compile. Install `requirements.txt` and `requirements-dev.txt` into a development virtual environment. Run:

```bash
python -m pytest -q
python scripts/build_release.py
```

Windows also needs Inno Setup 6:

```powershell
./packaging/windows/build-installer.ps1 -UseExistingBuild
./packaging/windows/smoke-installer.ps1
```

Linux packaging needs `dpkg-deb`; archive verification needs `desktop-file-validate` from `desktop-file-utils`:

```bash
python scripts/smoke_linux_installer.py
```

The workflow uses Windows runners and Ubuntu 22.04 Linux runners with Python 3.12 for packaging. Python 3.14 source compatibility is tested separately. The application runtime is included in each native build. See [RELEASING.md](RELEASING.md) for tagging, signing and draft publication.

## Downloads

| File | Purpose |
| --- | --- |
| `Pharma-Khaato-<version>-Setup-Windows-x64.exe` | Windows installation |
| `Pharma-Khaato-<version>-linux-amd64.deb` | Ubuntu/Linux Mint software installation |
| `Pharma-Khaato-<version>-linux-x86_64.tar.gz` | Linux per-user installation using the included `install.sh` |
| `*.sha256` / `SHA256SUMS` | Verify the downloaded package |
| `release.json` | Exact source revision, package sizes and hashes |

Linux tar installation creates `~/.local/bin/pharma-khaato` and an applications-menu entry. Close the app before upgrading. Run the included `uninstall.sh` to remove application files and shortcuts; shop data is preserved. Use the same installation method when upgrading. The `.deb` installs app binaries under `/opt/pharma-khaato` with a system menu entry; removal uses the system software manager.

## Shop records and backups

Application files and shop data are separate:

- Windows: `%LOCALAPPDATA%\Pharma-Khaato`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/pharma-khaato`

The `data` folder contains the SQLite database; `backups`, `receipts`, `exports`, `config` and `logs` are beside it. Updates and uninstall must preserve these folders. Never place the live database on a shared drive.

Use **Settings → Backup** to create a consistent backup while the app is running. Copy the completed backup to another device and verify recovery on a spare machine. Do not copy the live SQLite file while the app is running; active WAL records can be missed. Do not store records inside the executable or source-download folder.

[Real-device acceptance checklist](REAL_WORLD_READINESS.md) · [Simple first test](TRY_IT.md)
