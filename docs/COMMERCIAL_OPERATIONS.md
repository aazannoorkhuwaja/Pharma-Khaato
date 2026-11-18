# Owner recovery, update and release operations

Engineering procedures, 2026-11-12. These are proposed operating requirements, not a signed service agreement or completed deployment approval. Record named people and actual results in the acceptance worksheet before trading.

## Deployment profile

Candidate targets are Windows 11 x64 and Ubuntu 22.04/24.04 x86-64. The build matrix covers Windows and Ubuntu 22.04; Windows 11 and Ubuntu 24.04 installed behavior need independent acceptance. The installer's older minimum OS setting is not a support commitment. Do not promise macOS, Windows on ARM, or arbitrary thermal printers from source compatibility alone.

Use one authoritative host with locally attached storage, a separate OS account, full-disk encryption and owner-only filesystem access. Counters connect through authenticated TLS with an explicitly trusted shop certificate. Never share the live SQLite file over SMB/NFS. Keep the host clock correct. Test backup storage capacity and free space before opening a shift.

Before enabling trading, the owner and a qualified pharmacy reviewer must approve medicine metadata, expiry semantics, tax/discount and credit policies. Prescription-required products are blocked until an approved verification workflow is implemented. Managers cannot bypass that block. Changing a received product's base unit or pack conversion requires a separate catalog record; move physical stock only through reviewed inventory operations, preserving old history.

## Encrypted owner recovery copies

The Windows installer adds **Pharma Khaato - Owner Recovery** to Start. Linux provides the **Owner Recovery** desktop action. The installed executable also accepts `--recovery-tool`. The utility runs separately from the app/server and performs encryption/validation in a background worker.

1. Reconcile pending counter operations against the live host. Close the pharmacy desktop and stop its shop server. Preserve each counter's own pending configuration as part of the recovery plan; a host export cannot capture another computer's files.
2. Open Owner Recovery. Select **Export owner recovery copy**, the existing shop data folder and a new `.pkrecovery` file on protected off-device storage.
3. Enter an active account authorized to manage backups and a new recovery passphrase of at least 16 characters. Confirm the passphrase. Keep it separately under owner control; losing it makes this encrypted copy unrecoverable.
4. Export authenticates the owner, creates a fresh signed database backup, and encrypts the database, shop recovery key, selected configuration, TLS identity and receipts using AES-GCM with an scrypt-derived key. The utility refuses to replace an existing recovery file.
5. Test the copy on a disconnected replacement host. Select **Import**, its file and a new, nonexistent destination directory. Enter its passphrase. Authentication, file hashes, shop signature and database structure must pass before the new directory becomes available.
6. Close the utility. Configure the recovered installation to use the recovered data directory (`PHARMA_KHAATO_DATA_DIR`), verify the host address and TLS identity, and select an appropriate off-device backup destination. Use an OS launcher/environment configuration prepared by support; do not move a running database.
7. Keep the original host offline. Reconcile sales, credit, refunds, supplier accounts and stock against the last accepted checkpoint; count drawer cash and review unconfirmed operations. Record transactions lost since the snapshot rather than inventing completed sales. Reconnect counters one at a time and resolve their retained request identities.

Ordinary pre-login snapshot recovery still requires the matching shop recovery key plus a signed snapshot and authorized snapshot credentials; see [Recovery authority](RECOVERY_AUTHORITY.md). An arbitrary downloaded database cannot establish recovery authority.

The encrypted bundle has a 256 MiB / 10,000-file limit. For larger shops, support must use a tested, encrypted full-system/volume backup while the host is stopped, including the installed application version, data, config, receipts, recovery key and TLS identity. Restore that image onto an isolated machine and perform the same integrity/reconciliation checks before activation. This larger-store image procedure requires its own measured acceptance; do not split archives or remove receipts to bypass limits without an approved retention plan. Never sign an untrusted database to bypass provenance checks.

## Update and rollback rehearsal

1. Identify both installed and candidate versions, source revisions, installer hashes and signatures. Record the migration versions each supports. Finish and reconcile pending operations; suspend all counters.
2. Close the host and make a verified off-device recovery copy. Record stock, cash, customer and supplier balances and expected transaction counts using a sanitized acceptance fixture. Retain the matching old application installer.
3. Install the candidate on an isolated copy first. Verify schema checksums, migration evidence, historical financial reconciliation, permission matrix and all business flows. Review every conversion flagged by `financial_reconciliation.py`; genuine historical fractions below a paisa must be reconciled explicitly.
4. Rehearse power loss during download/install/startup/migration and disk-full failures. Confirm the original installation or preserved backup is recoverable. Test non-admin install, spaces in paths, reinstall, uninstall data retention, and all supported DPI/device combinations.
5. For a failed production upgrade, stop every counter and preserve the failed store for review. Restore the pre-upgrade data/config and matching old application together onto an isolated host. Installing an old executable against a newer database is intentionally refused. Reconcile any post-backup activity before resuming; do not discard it silently.
6. Activate only one reconciled host. Upgrade/reconnect counters together and verify version compatibility, TLS pinning, pending requests, receipts and cash-session ownership before opening sales.

See [Updates](UPDATES.md) for existing distribution behavior. There is no unattended production update or automatic rollback.

## Support and recovery objectives

Proposed pilot objectives: at most 15 minutes of recoverable trading loss (RPO) and restoration within 60 minutes (RTO). These are targets to measure, not claims that the current backup schedule achieves them. The owner must approve or replace these values, select an off-device schedule, verify retention/capacity, and time a full restore before adopting the objectives.

Assign a primary support contact, backup contact and escalation hours. During the controlled pilot, provide coverage whenever trading is open. Record backup success, age of last verified off-device copy and free space daily; review the encrypted-copy rotation and restore drill at least monthly. Keep at least one offline copy outside the workstation's failure/security boundary. Define retention with the owner and appropriate recordkeeping reviewer; do not delete records merely because an example schedule says so.

Stop trading for unexplained money/stock mismatch, unresolved checkout outcomes, suspected unauthorized access, corrupt data or inability to produce a verified backup. Preserve logs and operation IDs, keep the affected host isolated, and escalate. Generate the built-in support bundle; it excludes the business database by default. Inspect/redact it before sending. Share a full business database or recovery key only through an explicitly approved, secure support procedure.

## Release identity and approvals

Build on clean Windows/Linux runners with the pinned release dependencies. The workflow fails on dependency scanner errors/findings, missing runtime versions/licenses, and missing signing identity for tagged Windows builds. Configure `WINDOWS_CERT_BASE64` and `WINDOWS_CERT_PASSWORD` in protected GitHub secrets using an appropriate code-signing identity; never put them in source or an evidence worksheet. The signing script validates the resulting signatures. Record the publisher and signature verification of both app and Setup on a clean target machine.

The bundle includes runtime notices; separate artifact inventories hash packaged files. Review actual native Qt/OpenSSL/Python components and applicable distribution obligations, including whether additional notices/source obligations are needed. An MIT project license and generated inventory are not a completed third-party licensing review.

Create an exact-revision release evidence manifest:

```bash
python scripts/roadmap_acceptance.py acceptance/release.json --create --revision FULL_40_CHARACTER_COMMIT
python scripts/roadmap_acceptance.py acceptance/release.json
```

Create the `acceptance` directory first. Replace each `not_run` gate only after its named reviewer checks actual evidence. Put evidence files inside that directory and record their SHA-256 values; identify every installer by name and hash. Also complete the existing site trial worksheet and `scripts/release_acceptance_gate.py`. These tools check completeness, not authenticity. A human release owner must approve promotion; nothing in these procedures merges or deploys automatically.
