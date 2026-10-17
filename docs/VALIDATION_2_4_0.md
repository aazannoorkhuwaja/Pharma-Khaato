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
