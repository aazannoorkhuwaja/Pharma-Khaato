# Audit implementation checkpoint

Updated 2026-11-17. Working branch: `fix/audit-integrity`, based on `1dd242cebae3ca792750fc8dc91f03b84a7705ec`. Candidate version metadata: **2.5.1**. This is a review candidate, not an approved production release.

The six original audit reports remain historical findings against their pinned baseline. Implementation was subsequently authorized. The supplied UI ZIP and extracted samples are preserved. No live pharmacy migrations, automatic merge or deployment have been performed.

## Implemented in source

| Area | Changes |
|---|---|
| Sales and medicine safety | Trusted terminal identity for cash refunds; batch MRP enforcement; strict expiry validation; selected-lot allocation; cumulative refund rounding and zero-payout stock returns; shared refund preview; prescription-required sales blocked until an approved verification workflow exists. |
| Retry and concurrency | Preserve unknown outcomes/request identity for cash, credit and stock operations; concurrent checkout replay, last-unit sales, credit collection, supplier receipt and return/shift-close regressions. |
| Exact money and history | Migration 027 adds authoritative scaled integer columns with synchronized compatibility projections, bounds and reconciliation evidence. Genuine sub-paisa historical ledger amounts block migration. Ledger aggregates use integers. Migration checksums and complete declared-schema checks reject incompatible databases. Received base units and pack conversions cannot be changed. |
| Recovery and authorization | Process-lifetime OS store ownership; signed backups with independent shop recovery key; staged pre-login restoration; encrypted new-host recovery bundles and packaged owner utility; POSIX private directories; staff deactivation revokes sessions and unused manager approvals. |
| LAN resources | Bounded TLS connections, per-peer caps and total deadlines; authentication rate limits; session/cache limits and cleanup; direct service tests for terminal identity and lost responses. |
| Operator UI | Non-blocking settings/staff operations; explicit mixed-price lot selection; separate cart lines; fixed total placement and shortcut wrapping; accessibility labels/form buddies; explicit failed reports; repaired async-worker imports. |
| Release engineering | Strict dependency-audit/SBOM workflow; runtime/license and artifact inventories; mandatory signing identity for tagged Windows builds; evidence-manifest checks; recovery/update/rollback and device acceptance procedures. Pull requests now build review installers without publishing a release. |
| Installed 2.5.0 incident | Narrow compatibility for the redundant legacy 014 index history and observed legacy schema variants; frozen Linux GIO module isolation; printer startup/page/completion checks to stop false print success. Packaged smoke now checks fresh and legacy-history backups. |

## Current verification

- Full local run on 2026-11-17: **397 passed, 12 setup errors**, 139.88 seconds. Every error is in `tests/test_lan_service.py`, where the sandbox denies socket creation. There are no assertion failures. No tests were removed or skipped to obtain this result.
- Qt test fixtures are now installed; the earlier missing-fixture errors no longer apply to this run.
- Incident-focused run on 2026-11-15: 83 passed, one then-unavailable GUI fixture deselected. This is historical evidence, not the current full-suite count.
- Source functional smoke exercises setup/login, checkout/retry, receipts, fresh and legacy-history backups, TLS certificate creation and eight main screens.
- Earlier Linux UI matrix: 80 captures, 10 screen/scaling scenarios, zero critical anchor failures. It is not Windows or screen-reader acceptance, and does not prove exact sample-image equivalence.
- Earlier isolated service benchmark: 1,000 products and 200 sales across four worker counters, exact transaction/stock totals, approximately 59 ms p95. It excludes real network latency and sustained multi-machine load.
- Real 58/80 mm PDF rendering retained all 200 fixture lines. Actual printer/scanner behavior remains unverified.

## Work that is not completed

1. Build and validate the corrected installer against the exact release dependency environment. Local PyInstaller is unavailable and shell DNS/package downloads remain blocked. A review branch/PR is being prepared for connected CI; success must be checked on its exact commit.
2. Execute the 12 socket tests and real LAN fault/load acceptance outside the restricted sandbox.
3. Run the full dependency/native-component vulnerability and licensing review on shipped artifacts. Local cryptography differs from the selected release pin; local tests do not validate that upgrade.
4. Complete Windows/Linux installation, update, interrupted-upgrade and restore-based rollback acceptance using the actual artifacts; verify signing, filesystem ACLs and target Windows DPI.
5. Obtain qualified medicine-policy approval, historical fixture reconciliation, screen-reader/keyboard and sample-UI review, printer/scanner acceptance, measured recovery objectives and an observed operator pilot.

The prescription-safe default blocks restricted sales; a pharmacist-verification workflow is not implemented. Generated license inventories and acceptance templates do not constitute legal, clinical or owner sign-off. Broader architectural risks remain documented in the original audit; passing tests does not close them automatically.

Your installed 2.5.0 does not receive source edits automatically. It remains affected by its original backup failure until a compatible corrected package is installed. An owner-private, integrity-checked emergency database copy was created in `~/Pharma-Khaato-Recovery/`; the live store was opened read-only and was not repaired or migrated.

## Evidence and procedures

- [Installed 2.5.0 incident](docs/INCIDENT_2_5_0_BACKUP_AND_PRINTING.md)
- [Financial storage and reconciliation](docs/FINANCIAL_STORAGE.md)
- [Recovery authority](docs/RECOVERY_AUTHORITY.md)
- [Owner recovery, update and support procedures](docs/COMMERCIAL_OPERATIONS.md)
- [Dependency advisory review](docs/DEPENDENCY_SECURITY_REVIEW.md)
- [Target-machine UI and hardware acceptance](docs/UI_HARDWARE_ACCEPTANCE.md)

The entire commercial roadmap is **not yet complete**. No production-readiness claim is made from CI or local test counts alone.
