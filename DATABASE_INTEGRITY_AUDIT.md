# Database integrity audit

Audit evidence collected: 2026-11-10; reports finalized: 2026-11-11. Phase 1: analysis and documentation only.

Baseline: local `ui/reference-replica`, commit `1dd242cebae3ca792750fc8dc91f03b84a7705ec`, matching the GitHub branch at inspection. GitHub `main` was `1fc56654c5a69ae62525a13b17c6235568f6eee6`; findings target the audited branch, not an assertion that main has identical UI. No application code, live database, merge, deployment, or release changes were made.

Evidence labels: **Reproduced** = observed in a disposable database or recorded exact-commit CI; **Source-confirmed** = reachable behavior established by code inspection; **Risk** = plausible consequence requiring a targeted experiment; **Unverified** = missing acceptance evidence. Severity reflects business impact, not exploitability alone. Complexity: S = 1–2 engineering days; M = 3–5; L = 1–2 weeks; XL = multiple weeks. Estimates exclude independent acceptance, regulatory review and rollout; overlapping fixes must not simply be summed.

## Integrity assessment

SQLite write transactions and online backup APIs are useful foundations. Financial safety depends on additional semantic invariants, exact outcome handling, and exclusive recovery ownership. All destructive experiments below used newly created temporary stores.

## D01 — Restore accepts a structurally incomplete current-version database

- **Severity / impact:** Critical — restoration reports success but leaves required operations unavailable.
- **Evidence status:** Reproduced
- **Location:** [core/backup_service.py:161](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/backup_service.py#L161); [core/backup_service.py:318](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/backup_service.py#L318); [core/migration_manager.py:88](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/migration_manager.py#L88).
- **Evidence:** Dropping Return_Operation from a snapshot while retaining migration history passed validation (True, "ok"). restore_database returned success; the restored table count was zero. The validator checks a limited table set rather than the complete declared schema.
- **Reproduction / verification:** Copy a disposable initialized DB using SQLite backup, drop Return_Operation, validate and restore that copy. Never perform this on a shop store.
- **Recommended correction:** Validate complete versioned schema and critical constraints/indexes before replacement; reject inconsistent migration history; run semantic financial/stock reconciliation and reopen verification before declaring restore successful.
- **Regression tests needed:** Missing required table/column/index/trigger; tampered migration rows; newer schema; corrupt backup; disk full; interrupted replacement; old database remains recoverable; restored checkout/return/credit smoke tests.
- **Implementation complexity:** L.

## D02 — Malformed legacy expiry values are treated as sellable

- **Severity / impact:** High — medicine with unknown expiry can be dispensed.
- **Evidence status:** Reproduced conditional on malformed stored data
- **Location:** [core/pos_service.py:147](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/pos_service.py#L147); [core/inventory_service.py:205](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/inventory_service.py#L205).
- **Evidence:** Setting a disposable batch expiry to "not-a-date" allowed checkout because the sale query relies on text ordering. Normal inventory input validation reduces ordinary creation risk but does not protect legacy/restored data.
- **Reproduction / verification:** Inject malformed expiry into a scratch batch and check out; see INVALID_LEGACY_EXPIRY probe.
- **Recommended correction:** Fail closed on invalid expiry at authoritative allocation, quarantine invalid legacy lots during preflight, and enforce canonical dates on migration/import.
- **Regression tests needed:** Invalid text, impossible calendar dates, blank/null, ISO timestamps, month-only legacy policy, leap days, expiry today/tomorrow, timezone boundary and FEFO ties.
- **Implementation complexity:** M.

## D03 — Money persistence mixes REAL values with integer-minor-unit ledgers

- **Severity / impact:** High risk — cumulative rounding and reconciliation can diverge. No ordinary-volume cent drift was demonstrated.
- **Evidence status:** Risk
- **Location:** [schema_sqlite.sql:5](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/schema_sqlite.sql#L5); [core/pos_service.py:270](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/pos_service.py#L270); [core/supplier_service.py:13](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/supplier_service.py#L13).
- **Evidence:** Several monetary columns remain SQLite REAL; Python Decimal calculations and float persistence are not a uniform exact-money storage contract. Supplier minor-unit handling demonstrates a different representation.
- **Reproduction / verification:** Inspect column types and aggregate fractions repeatedly in a disposable database; compare ledger sums to a Decimal reference using documented rounding.
- **Recommended correction:** Define currency, rounding and cost precision centrally; migrate money to scaled integers with pre/post reconciliation and reversible migration artifacts. Preserve higher precision for unit costs where necessary.
- **Regression tests needed:** Large totals; repeated 0.1/0.01 entries; split tenders; discount/tax ties; partial refunds; migrated historical balances; maximum supported amount and overflow.
- **Implementation complexity:** XL.

## D04 — Migration history can mask schema drift and downgrade incompatibility

- **Severity / impact:** High risk — damaged or newer stores may open under incompatible code.
- **Evidence status:** Source-confirmed permissive behavior; resulting corruption untested
- **Location:** [core/migration_manager.py:88](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/migration_manager.py#L88); [core/db_engine.py:165](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/db_engine.py#L165).
- **Evidence:** Migration completion is identified by names without content hashes; duplicate-column/already-exists handling can suppress inconsistent states. Normal startup does not establish the same explicit newer-schema refusal expected for safe rollback.
- **Reproduction / verification:** On disposable fixtures alter a migration-created object or mark a missing object as migrated; launch older schema expectations against a newer fixture.
- **Recommended correction:** Version schema manifests and checksums; narrowly assert acceptable historical exceptions; reject unknown newer schemas before mutations and require a coordinated backup-based downgrade procedure.
- **Regression tests needed:** Every supported upgrade path; altered migration body; partial migration; duplicate objects with wrong shape; downgrade refusal; power failure at each migration boundary.
- **Implementation complexity:** L.

## D05 — Maintenance exclusivity does not cover separate host processes

- **Severity / impact:** High risk — restore/migration can race another process using the same store.
- **Evidence status:** Risk; multi-process destructive experiment not executed
- **Location:** [core/db_engine.py:70](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/db_engine.py#L70); [ui/app/application.py:9](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/app/application.py#L9); [scripts/run_shop_server.py:14](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/scripts/run_shop_server.py#L14).
- **Evidence:** Database maintenance uses an in-process guard. The GUI process lock is not a demonstrated shared ownership lock covering the standalone shop-server entry point.
- **Reproduction / verification:** In isolated subprocesses attempt GUI/CLI ownership of the same data directory; hold a second connection while staging restore. Never test on live data.
- **Recommended correction:** Use one shared data-directory ownership/maintenance protocol across all entry points; drain requests, close connections and verify exclusive ownership before file replacement.
- **Regression tests needed:** Two CLI hosts; GUI plus CLI; stale lock recovery; separate data directories; Windows open-file behavior; Linux old-inode writes; interrupted maintenance.
- **Implementation complexity:** L.

## D06 — Backup scope omits operational identity and pending state

- **Severity / impact:** Medium — disaster recovery can strand counters or lose retry context.
- **Evidence status:** Source-confirmed scope; recovery-on-new-host outcome untested
- **Location:** [core/backup_service.py:189](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/backup_service.py#L189); [core/path_manager.py:46](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/path_manager.py#L46); [core/lan_config.py:13](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/lan_config.py#L13).
- **Evidence:** SQLite backup does not itself capture TLS identity, counter trust configuration, and filesystem pending-operation journals. A database restore is not a complete shop-host recovery package.
- **Reproduction / verification:** Restore a database snapshot onto a disposable clean host profile; verify counter pinning, settings, pending receipts and operations.
- **Recommended correction:** Document and implement a protected recovery bundle or explicit key rotation/re-enrollment procedure; define RPO/RTO and include a verified manifest.
- **Regression tests needed:** Same-host/new-host recovery; lost TLS key; expired certificate; outstanding operation; partial bundle; retention/storage exhaustion; encrypted export and key recovery.
- **Implementation complexity:** L.

## D07 — Global connection guard limits concurrency

- **Severity / impact:** Medium — long reads or backup work may delay all counters.
- **Evidence status:** Risk; throughput not benchmarked
- **Location:** [core/db_engine.py:251](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/db_engine.py#L251).
- **Evidence:** An application-wide lock surrounds database access, serializing in-process work beyond SQLite writer serialization.
- **Reproduction / verification:** Benchmark concurrent report/search/checkout/backup requests against disposable representative-size data; record p50/p95/p99 and lock wait.
- **Recommended correction:** Measure first; keep writes short, use safe independent read connections where supported, and bound report/backup work and retry budgets.
- **Regression tests needed:** Busy timeout, concurrent last-unit checkout, report during sale, backup during close, cancellation and slow disk; prove no oversell and bounded response time.
- **Implementation complexity:** L.

## Additional verification obligations

Review legacy unit-price backfill in migration 013 against original receipts: current-product prices cannot establish historical per-line allocation. Treat historical refund accuracy as unverified until reconciled. Product base-unit/conversion edits require explicit stock/history semantics; do not reinterpret existing units silently. Database CHECK constraints and immutable financial history should be reviewed alongside service invariants; direct file access is an OS trust boundary, not a demonstrated LAN bypass.

A01–A04 in the architecture report are also database-integrity findings. The test matrix covers cash-shift races, duplicate stock receipt, customer credit payments/returns, supplier balances, and stock-ledger reconciliation.
