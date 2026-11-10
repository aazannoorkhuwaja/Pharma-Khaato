<!-- coderabbit-ai-generated:v1 -->

# First test release: Pharma Khaato 2.5.0

This is a supervised practice release for Windows x64 and Ubuntu 22.04/24.04 x86_64. It is not approval for live dispensing or real payment collection. Physical pharmacy acceptance is pending. The GitHub release is marked **Pre-release** and the app will not offer it as a stable update. Future fixes receive a new version; do not replace this version's published binaries.

## Download and identify the build

Use the assets attached to the [2.5.0 test release](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/tag/v2.5.0). Windows testers need `Pharma-Khaato-2.5.0-Setup-Windows-x64.exe`; Ubuntu testers normally need `Pharma-Khaato-2.5.0-linux-amd64.deb`. The tar archive is an alternative Linux installer. No Python installation is needed.

Read `Windows-SIGNING.txt` before installing. An unsigned build is for supervised testing; do not disable Windows protection. If your workstation blocks installation, record the message and ask the release owner for a signed build.

Compare the download's SHA-256 to its `.sha256` file or `SHA256SUMS`. On Windows, use PowerShell `Get-FileHash <download> -Algorithm SHA256`; on Linux, use `sha256sum -c SHA256SUMS` in a folder containing all three packages. Keep `release.json`, which identifies the exact source revision and hashes. After installing, verify **About → 2.5.0**.

## Start safely

1. Use a spare computer or a separate operating-system test account with synthetic records. A normal installer upgrade preserves the current account's shop data; it does not create a separate practice database.
2. If testing an upgrade, create and restore an external backup on a spare computer before installing. Record the old version and opening record counts/balances. Do not copy an open live SQLite file by itself.
3. Assign a test lead, a cashier and a supervisor. Agree how they contact the release owner during the trial. Do not start an unattended shop trial without a reachable support contact.
4. Create an owner login and a separate cashier. Check shop details, tax rules, receipt width and printer. Use practice values agreed by the supervisor.
5. Add suppliers and medicines, with pack/unit conversion and expiry. Receive only independently counted practice stock. Set customer opening dues only from a reconciled ledger.

## Opening balances and cutover

Record the count and valuation of stock, customer dues, supplier debts and cash separately, then reconcile the app against them. Receiving an invoice creates stock and supplier payable entries; do not enter an old supplier debt as a new stock invoice merely to copy its balance. This release has no approved historic supplier-balance migration procedure. A real shop with historic debts must keep its existing ledger and obtain an agreed migration plan before cutover. Do not claim that a fresh test database proves an existing shop migrated correctly.

## Run the test

Follow [TRY_IT.md](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/v2.5.0/docs/TRY_IT.md) for the worked stock/sale/return example, then the 34 cases in [PHARMACY_SITE_ACCEPTANCE.md](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/v2.5.0/docs/PHARMACY_SITE_ACCEPTANCE.md). Include:

- Cash sale, exact/change payment, card/wallet, credit sale and collection, held bill, refund, supplier receipt and shift close. Independently reconcile stock, dues and drawer cash.
- Card, Easypaisa and JazzCash are recorded payment methods. Confirm payment in the provider's own system; this app does not collect or verify the money.
- Scanner rapid/pack scans, actual 58/80 mm receipt printer, paper/disconnect/reprint, and the shop monitor at Windows 100/125/150% scaling. Reprint a committed bill instead of creating another sale.
- Choose a second backup folder in Settings. A same-volume warning means a disk failure may lose both copies. A different volume is not proof of a separate physical disk. Check the device physically, unplug it to verify the warning, reconnect, create a backup, and restore on a spare computer.
- Automatic snapshots are checked each minute and taken at least hourly while the app is open. Work since the last successful backup can be lost. Make a manual backup after important entry and at shift end. Protect copies with OS/device access controls and encryption; the app's SQLite backup files are not encrypted by the app.
- If using LAN counters, test simultaneous last-unit checkout and a network interruption using practice records. Counters require the main shop computer and LAN; they cannot independently sell while disconnected.

Stop the trial for duplicate sales, wrong totals/stock/balances, missing records, unauthorized access, failed restore, or inaccessible checkout. Preserve evidence and contact the test lead. Do not retry an uncertain bill as a new sale; use the app's pending-operation check.

## Report a result

Use the attached `site-acceptance.json` worksheet. It starts with all cases `not_run`; record genuine results and evidence, including version, revision, checksum, OS, monitor scale and hardware models. Keep completed worksheets and screenshots private if they contain shop or staff information. The worksheet is a test record, not regulatory certification.

Report reproducible software faults through [GitHub Issues](https://github.com/aazannoorkhuwaja/Pharma-Khaato/issues) with synthetic steps, expected/actual result, version, operating system and a redacted screenshot. Never attach a database, receipt archive, password, customer details or an unreviewed support bundle publicly. Agree a private support route with the release owner for sensitive incidents; no response-time commitment is implied.

## Before a live deployment

Required owner actions remain: actual printer/scanner/display acceptance; external-device restore rehearsal; reconciled opening balances; trained operators; a reachable support contact; trusted Windows signing for broad distribution; and qualified review of local pharmacy, tax and privacy requirements. Full Urdu, automatic FBR reporting, independent offline counters and multi-branch synchronization are not included. Use the existing system until the supervisor approves the actual deployment.
