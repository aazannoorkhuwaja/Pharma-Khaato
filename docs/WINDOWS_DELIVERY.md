# Windows-first delivery and pharmacy pilot

The main customer target is Windows 10 version 1809 or later and Windows 11, on 64-bit Intel/AMD PCs. This excludes Windows 7/8, 32-bit Windows and an untested native ARM build. Windows 10 compatibility does not replace Microsoft's OS security-support requirements.

## Getting a test installer

Open **Actions → Build Windows and Linux installers → Run workflow**, choose `main`, and run it. After the green result, download **Windows-installer** from the run's **Artifacts** section. Extract the ZIP. It contains the Setup EXE, its checksum and the getting-started guide. Merges into `main` also start this build automatically. No tag or public release is needed for a private test.

## What the tester receives

Give the tester `Pharma-Khaato-2.4.0-Setup-Windows-x64.exe`, its SHA-256 sidecar and the installed Getting Started guide. Do not ask the tester to install Python, Git or run terminal commands. Keep Urdu/Sindhi translation deferred until the English workflows have been reviewed.

The installer uses a per-user folder under `%LOCALAPPDATA%\Programs`, needs no administrator password, offers a desktop shortcut by default and adds the app and guide to the Start menu. App data stays separately under `%LOCALAPPDATA%\Pharma-Khaato`, outside the install directory. Use the same Windows account each day; another Windows account has different shop data. Do not run the app as Administrator as a workaround.

The installer does not remove shop data during reinstall/uninstall. Back up before upgrades anyway. Windows reinstallation, disk failure and deleting the Windows account are separate risks. Never uninstall or reset data merely to diagnose a sign-in or printer issue.

For the first pilot, use test stock and transactions. Before live sales, verify real opening stock, customer dues, supplier balances and tax settings. Complete the [shop acceptance checklist](REAL_WORLD_READINESS.md). Install the printer manufacturer's Windows driver and test the scanner on the actual machine. Keep Windows security enabled; an unsigned test build may need the supplier to verify the download before proceeding. The workflow supports code signing when a trusted publisher certificate is configured; see [RELEASING.md](RELEASING.md).

## Engineering build

On a Windows build machine install 64-bit Python 3.12 and Inno Setup 6. From the repository root:

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File packaging/windows/build-installer.ps1
powershell -ExecutionPolicy Bypass -File packaging/windows/smoke-installer.ps1
```

These commands are for the developer, not the pharmacy operator. Build in a disposable Windows environment. The installer test installs an isolated app, verifies the installed executable, creates a test database outside the install folder, reinstalls and uninstalls, checking that the test database survives byte-for-byte. It does not prove an upgrade from every historical release or physical power-loss recovery.

A local installer build makes a fresh native package by default. `-UseExistingBuild` is reserved for a package already built in the same controlled run. Missing Inno Setup is a hard error: a portable ZIP alone is not treated as delivery of the customer installer.

## Automated gates

Development CI now runs on both Windows and Linux. The full matrix also checks Python 3.12 and 3.14; GUI smoke runs on Windows as well. The release workflow builds the Windows executable, requires a successful machine-readable functional report, compiles the Setup EXE, runs installed/reinstalled functional checks and verifies data retention after uninstall before uploading artifacts. Workflow artifacts are review downloads, not automatically published releases.

## Verification status

The current workspace is Linux. Source tests and the updated reporting/build logic can be checked here; PowerShell, Inno Setup, native Windows installation and Windows printer drivers cannot be executed here. The Windows workflow must pass on the exact proposed source revision before handing an installer to the pharmacy tester. The owner reported that both Windows Python checks passed before merging the previous fixes. That confirms the reported source-test result, not a successful installer build. The installer build and real printer/scanner checks still need their own passing results.
