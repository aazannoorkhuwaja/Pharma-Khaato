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
