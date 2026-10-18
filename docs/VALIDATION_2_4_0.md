# 2.4.0 integration evidence

Verified in the cloud Linux workspace on 17 October 2026 (UTC), using Python 3.12.14 and Qt/PySide6 6.7.2. This records engineering checks; native Windows and physical shop acceptance remain open as listed in [Real-world readiness](REAL_WORLD_READINESS.md).

| Check | Result |
| --- | --- |
| Full pytest regression suite | 217 passed in 28.12 seconds |
| Follow-up supplier, cross-session, disconnected-counter and MVC checks | 13 passed |
| Isolated demo business flow | All seven stages passed |
| Offscreen GUI | Login and all eight main screens opened; screenshots captured |
| Supplier dialogs | Accounts, product/unit lookup, decimal invoice display and screenshots passed |
| UI source audit | All six layout/theme checks passed |
| Compilation and Git whitespace checks | Passed |
| Disposable installed functional smoke | Migrations, login, stock, cash, sale replay, saved receipt, TLS certificate and eight screens passed |
| Isolated smoke with an invalid external shop URL configured | Passed without contacting that shop |
| Linux PyInstaller executable | Functional smoke passed |
| Windows installer and physical printer/scanner/drawer | Not tested in this Linux cloud environment |

The source smoke uses a temporary shop and forces local routing. Demo and GUI scripts use `.demo-data`; no real shop database is included in the release. The release script runs the frozen functional smoke before producing the versioned archive and SHA-256 sidecar. Release artifacts are generated locally under `release/`; they have not been published or deployed.

Operator instructions: [Quick start](OPERATOR_QUICK_START.md).

## Windows-first delivery follow-up

The source suite now passes **222 tests** (29.49 seconds in this Linux environment), including build-script startup without a custom PYTHONPATH, Windows data-folder selection and rejection of windowed executables that exit without a valid success report. A fresh PyInstaller build passes the updated report-based functional smoke. Windows CI/release gates and installer smoke scripts are configured but have **not run in this Linux workspace**. See [Windows delivery](WINDOWS_DELIVERY.md) for the exact pending native checks.

## Credits and optional updates follow-up

The full Linux regression suite passes **238 tests** (29.19 seconds), including strict version handling, draft/prerelease and missing-installer rejection, offline recovery, successful-check throttling, official release-page construction, deferred notices during a cart/pending bill, manual checks after opting out, plain-text release notes and license-matching builder credits. Follow-up update/MVC checks pass **20 tests**. Offscreen screenshots verify the About/credits and update dialogs; all eight main screens and the layout audit pass. The packaged functional smoke also verifies the new dialogs. Native Windows and physical-device gates remain open.

## Windows restore failure follow-up

The supplied Windows Python 3.12 CI log reported six restore/recovery failures with `OSError: [Errno 9] Bad file descriptor`; the other 232 tests passed. The staged SQLite file was reopened read-only before `os.fsync`. Windows requires a writable descriptor for this flush. Restore now uses `r+b`, which preserves the staged bytes and permits the flush.

A regression reproducing the Windows descriptor restriction failed before the fix and passes afterwards. A separate disk-flush failure check verifies that restore still aborts and preserves current shop records. All 20 backup/recovery checks and the full **240-test suite** pass locally on Linux (28.86 seconds for the full suite). Native Windows CI must rerun on the fix before the Windows gate can be considered green.

## Simpler first-use follow-up

Based on merged main `61f39ab`, all **240 tests** pass locally (28.92 seconds), along with the eight-screen GUI check, disposable functional check, layout audit, compilation and documentation-link checks. Wording-only test expectations were updated to match Owner and Check This Bill; backend role and payment values remain unchanged. The owner reports that both Windows source CI jobs passed before the earlier merge. The simplified installer workflow still needs its own native Windows build result; source CI alone does not produce or validate a Setup EXE.

## Packaged-check timeout follow-up

The supplied Windows build log shows that PyInstaller completed the EXE successfully, followed by a 60-second timeout in the packaged functional check. A Windows-style file-lock regression reproduced an unhandled cleanup error: log handlers still held files inside the disposable check folder. The check now closes only its own temporary log handlers before folder deletion, drains background screen work, and records progress stages. Functional-check exceptions return a structured failure report rather than escaping to the windowed executable's exception dialog. Failed installer runs retain diagnostic files without including test databases or private keys.

The regression fails before the fix and passes afterwards. All **243 tests** pass locally on Linux (29.68 seconds), and a fresh PyInstaller executable passes the functional check. Native Windows must rerun to confirm the timeout is resolved there; installer publication remains gated by that result.

## Worker database handle root-cause follow-up

The next supplied Windows log reports **242 passed, 1 failed**, with `WinError 32` naming the temporary `pharmacy_db.sqlite`. The earlier log-file cleanup fix was incomplete: `reset_thread_connections()` closes only the caller's connection, whereas the Qt screen checks leave persistent SQLite connections registered from background threads. Those handles survive until process exit and prevent Windows from deleting the temporary database.

The strict cleanup regression now tracks **all SQLite connections**, not just log files. It reproduced the open-database error on Linux before the fix. Shutdown and the disposable check now use a shared, guarded `close_all_connections()` operation. It waits for managed transactions and rejects unfinished legacy transactions instead of discarding work. Cursors close when their transaction context ends; failed connection initialisation closes its unregistered handle. Tests also verify that the same worker thread can reconnect after shutdown and that a committed write survives.

All **247 tests** pass locally on Linux (31.76 seconds), plus the GUI and fresh PyInstaller functional checks. No cleanup errors were ignored, no garbage-collection workaround was added, and no timeout was increased. Native Windows CI must still confirm the fix on its own runner.


## Python 3.14 native shutdown crash

Both supplied PR logs show the same disposable-check subprocess failing with a native crash (Linux SIGSEGV; Windows access violation), while the other 246 tests pass. Reproduced locally with Python 3.14.8 / PySide6 6.12.0, including a full-suite failure. Python faulthandler identifies `QWidget::destroy` inside `PySide::destroyQCoreApplication` at interpreter exit. Closing the test windows only hid them; retained window objects reached native shutdown cleanup.

The check now tracks its screens and dialogs, waits for workers, schedules their destruction and flushes deferred-delete events while QApplication is alive, including failure cleanup. The subprocess regression additionally asserts no top-level windows survive and enables native fault diagnostics. Existing strict log-file and SQLite-handle assertions remain intact.

After the fix: **247 passed** on Linux Python 3.12 (34.57 seconds), **247 passed** on Linux Python 3.14.8 / Qt 6.12.0 (35.03 seconds), and **15 consecutive runs** of the three cleanup checks passed. A fresh PyInstaller executable and the eight-screen GUI check also passed. Windows CI must confirm the updated branch; these local results do not establish a native Windows result or a published release.

## Windows and Linux release preparation

Reference review used `aazannoorkhuwaja/FlashYT`: its download-first README, short install steps and native-artifact collection informed the release structure. Pharma Khaato builds a self-contained Linux application, adds verified checksums and source identity, and keeps publication as a reviewed draft because pharmacy hardware and opening balances need acceptance.

On the release-preparation branch, all **255 tests** passed locally on Linux Python 3.12 (32.69 seconds) and Python 3.14 (32.67 seconds). New checks reject incomplete/tampered release assets and ensure Linux update notices require Linux downloads. Both GitHub workflow files pass GitHub Actions schema validation; updated documentation links, shell syntax, compilation and the UI source audit pass.

A fresh native build produced the Linux archive and Debian package with matching SHA-256 files. The archive passed actual per-user install, installed functional verification, missing-source failure safety, reinstall and uninstall checks, preserving a real migrated synthetic shop database byte-for-byte. Paths contained spaces. The Debian package passed root-ownership/launcher/desktop-entry inspection, extraction and functional verification of its extracted executable. The eight-screen GUI check also passed.

These runs used Debian 13 in the cloud, not an Ubuntu 22.04 release machine. CI builds the distributed Linux packages on Ubuntu 22.04 and additionally performs real Debian-package installation/reinstallation/removal plus X11/xcb verification under Xvfb. Those native CI checks, the Windows installer/signing checks and the physical pharmacy acceptance record remain pending on this revision. No stable release, signing result or real-device acceptance is claimed from these local tests.

## First-use and preserved-account follow-up

The tester confirmed that the Linux computer had run an older version. Startup checks the existing shop's employee registry and correctly preserves that account rather than replacing it. Demo credentials are not normal installation credentials. No device database, password or records were accessed or reset during this investigation.

A verification gap was found: the installed smoke created an owner through backend code instead of exercising the actual setup and sign-in forms. It now fills and submits the real owner form, verifies that setup is no longer needed, and signs in through the real asynchronous sign-in UI before checking shop operations. New regressions cover setup cancellation, owner creation with a chosen password, the startup transition into sign-in, existing-account preservation and help that does not modify credentials. Sign-in help explains preserved accounts and the absence of default credentials. The practice guide documents a separate Linux shop folder, preserving the original.

All **260 tests** pass locally on Python 3.12 (34.74 seconds) and Python 3.14 (34.12 seconds). A fresh PyInstaller executable passes the expanded functional check, including the real setup and sign-in screens. The UI audit and compilation pass. Native Windows/Ubuntu installer CI must run on the review branch; the original user's existing password remains unknown and unchanged.
