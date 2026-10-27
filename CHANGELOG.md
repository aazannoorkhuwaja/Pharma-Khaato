# Changelog

All notable product changes are recorded here. Dates refer to the engineering/release line; a build is not a production release until its launch-candidate gates and manual hardware acceptance are complete.

## 2.4.1 — Launch candidate, physical acceptance pending

- Added a read-only accounting reconciliation that re-derives stock totals, saved sale arithmetic, customer credit balances, refund limits, closed-shift cash and orphaned rows from the records themselves, and reports as a failure in the launch self-check when any identity no longer holds. It stays silent on healthy data and is covered in both directions.
- Unified money quantization in `core/money.py`; reports, drawer reconciliation, receipts and ledgers now share one quantum. Added a regression that proves a 3,000-line float drift case collapses back to the exact total, and one that proves no two money helpers can disagree by a cent.
- Audit rows are now stamped in shop time like the cash-shift events in the same table, so an audit trail can be ordered against the shift it belongs to whatever the workstation clock says. Receipt and print timestamps fall back to shop time too.
- A fresh installation whose base schema file is missing now stops with an operator-facing message instead of silently creating a database with no tables.
- A migration that collides with an existing column or object is tolerated only while upgrading an existing shop, and is now reported at warning level; on a fresh database it is raised. Added schema-parity checks covering every applied migration, the seeded walk-in customers and default settings, and fresh-versus-upgraded schema equality.
- Removed the legacy MySQL statement rewrites and bounded the statement cache; dropped unused imports left over from that era.
- Removed obsolete MySQL/XAMPP-era artifacts and the superseded audit and migration-plan documents; corrected the database documentation to describe the money representation and schema ordering that actually ship.
- Repaired the migration and security verification scripts, which were failing on the committed branch: the security suite no longer runs against a real application-data folder or performs a backup/restore there. Full evidence, including the live shared-counter check, is recorded in [docs/LAUNCH_CANDIDATE.md](docs/LAUNCH_CANDIDATE.md).

## 2.4.0 — Engineering build, shop acceptance pending

- Added sign-in help explaining existing accounts, preserved records and the absence of a default password.
- Release verification now completes the real owner-setup form and signs in through the real sign-in screen before exercising shop operations. Startup regressions cover setup cancellation, successful first use and existing-account preservation.
- Added instructions for testing a separate Linux practice shop without replacing old shop records.

- Added native Windows/Linux release preparation: Windows Setup, an Ubuntu-compatible Debian installer and a Linux per-user archive, each with checksums. Tag builds prepare a draft only after both platforms and runtime compatibility checks pass.
- Added Linux installation/reinstallation/data-retention checks, explicit package permissions, failed-copy protection, and optional validated Windows app/installer signing before final checksums.
- Made download and first-use instructions platform-specific; corrected obsolete deployment and live-database-copy guidance. Linux update notices now require a Linux package instead of a Windows installer.

- Fixed intermittent Python 3.14 / Qt 6.12 crashes at the end of installer verification. Disposable windows are explicitly destroyed while Qt is running, after background work finishes.

- Fixed Windows cleanup retaining the SQLite database through background-thread connections. Shutdown now drains active work and closes every managed connection; transaction cursors and failed database initialisation also release their handles.

- Fixed disposable installed-app checks leaving temporary log handles open on Windows. Failed windowed checks now return an error report instead of opening an exception dialog; build failures retain stage/error details.

- Shortened the README and daily-use guide; added an exact practice-bill exercise. Replaced technical setup and recovery wording with owner, bill and cash-entry instructions.
- Added automatic Windows test-installer builds for main and pilot review branches, with a single installer download containing Setup, checksum and a short guide. No public release is required for testing.

- Fixed Windows backup restoration failing with `Bad file descriptor`: staged databases now use a writable, non-truncating handle for the required durable flush. Restore still aborts safely if that flush fails.

- Added visible builder credits matching the MIT license and optional background update checks with plain-language release notes, Later/download choices, and a workstation opt-out. Billing remains available offline.

- Made Windows the primary delivery target: per-user installer, default desktop shortcut, installed getting-started guide, Windows development CI, and native install/reinstall/data-retention gates.
- Require a positive functional-check report for windowed executables; installer builds fail if the Setup compiler is unavailable and rebuild packages by default.

- Enforced atomic, durable checkout and return replay; saved original receipt content and exact historical line amounts.
- Added explicit tax review, cash tender validation, scoped manager approvals and counter-specific cash shifts.
- Added tablet/strip/box stock units, pack barcodes, lot prices, counted/block stock, supplier invoices, payments and return credits.
- Simplified customer accounts to name-first identity with optional phone/CNIC, account repayments and auditable corrections.
- Added authenticated TLS local counters with terminal-bound permissions, durable pending operations and local printing.
- Hardened backup, restore, corruption recovery, startup locking and legacy migration safety; aligned financial dates to Pakistan shop time.
- Added recovery-first cashier workflows, focused regression coverage and installed functional smoke. See operator and readiness guides for limitations and physical acceptance steps.

## 2.3.1 — Launch candidate

### Product experience
- Reworked the desktop shell around pharmacy tasks instead of database terminology.
- Added responsive full/compact/mini navigation, consistent table ergonomics and task-focused copy.
- Added a product-grade sign-in surface, visible installed version and About Pharma Khaato information.
- Added pharmacy profile settings for receipt identity, address, phone, licence and tax registration.
- Added five selectable thermal receipt layouts with preview, including Professional 80 mm and Compact 58 mm.
- Simplified staff administration to selected-row actions instead of embedded action buttons.

### Performance
- Added lazy/cache-aware screen navigation and background task execution for slow database/file operations.
- Added bounded inventory/customer/ledger reads, debounced searches and stale-result protection.
- Added exact indexed barcode lookup, FTS-backed product search and query-specific SQLite indexes.
- Reduced SQLite lock waiting so a busy database fails clearly instead of making the counter appear frozen for an extended period.

### Sales, cash and credit correctness
- Corrected physical-drawer accounting so card/Easypaisa/JazzCash sales do not count as cash.
- Added durable customer-credit repayment history with payment method and cash-session attribution.
- Added durable checkout-request lifecycle/idempotency to protect against duplicate sales after uncertain retries.
- Preserved sale-time line values for return/history correctness.
- Added durable held-sale lifecycle and crash recovery.

### Returns & inventory
- Added controlled customer returns/refunds with quantity caps, stock restoration and credit adjustment.
- Added indexed FEFO sellable-stock lookup and expiry filtering.
- Added full-catalog search while keeping initial inventory rendering bounded.

### Reliability & recovery
- Added ordered transactional migrations, duplicate migration-version guard and corrected SQLite trigger parsing.
- Added automatic daily integrity-checked backups with retention.
- Added guarded in-app restore with a safety backup before restore and required application restart.
- Added launch self-checks, isolated demo data, business-flow smoke tests and major-screen GUI smoke tests.
- Added per-data-directory single-instance protection for interactive desktop use.
- Added privacy-conscious support diagnostics bundles that exclude the live database and business exports by default.

### Release engineering
- Added native PyInstaller package smoke testing and SHA-256 release checksums.
- Added a versioned Windows Inno Setup installer path with stable upgrade identity and optional desktop shortcut.
- Expanded PyInstaller hidden-import coverage for all lazy-loaded production screens/services.
- Added full Windows/Linux pull-request compatibility gates alongside the faster development gate.

### Security
- Centralized backend role/action authorization for sensitive business operations.
- Maintained PBKDF2-HMAC-SHA256 credential hashing and persistent login lockout.
- Added production security and support documentation.

### Manual acceptance still required
- Validate the exact thermal printer and paper width.
- Validate the intended barcode scanner.
- Validate any connected cash-drawer workflow.
- Complete one clean-install/rehearsal on the target production workstation before first live use.
