# Commercial readiness roadmap

Audit evidence collected: 2026-11-10; reports finalized: 2026-11-11. Phase 1: analysis and documentation only.

Baseline: local `ui/reference-replica`, commit `1dd242cebae3ca792750fc8dc91f03b84a7705ec`, matching the GitHub branch at inspection. GitHub `main` was `1fc56654c5a69ae62525a13b17c6235568f6eee6`; findings target the audited branch, not an assertion that main has identical UI. No application code, live database, merge, deployment, or release changes were made.

Evidence labels: **Reproduced** = observed in a disposable database or recorded exact-commit CI; **Source-confirmed** = reachable behavior established by code inspection; **Risk** = plausible consequence requiring a targeted experiment; **Unverified** = missing acceptance evidence. Severity reflects business impact, not exploitability alone. Complexity: S = 1–2 engineering days; M = 3–5; L = 1–2 weeks; XL = multiple weeks. Estimates exclude independent acceptance, regulatory review and rollout; overlapping fixes must not simply be summed.

## Release decision

**Do not promote the audited commit to a commercial production release.** Financial/refund and recovery defects are reproduced, UI CI is failing, and essential operational acceptance is incomplete. This is an engineering release recommendation, not a legal or regulatory certification.

Existing assets include release workflows, packaging scripts, installer smoke tests, checksum/provenance work, update/support documentation and a release-approval gate. Their existence is not evidence that the exact downloadable artifact has passed a real pharmacy acceptance run.

## C01 — Commercial signing and upgrade/rollback acceptance remain incomplete

- **Severity / impact:** High — users may install unauthenticated artifacts or recover incorrectly after an incompatible update.
- **Evidence status:** Source-confirmed workflow policy; shipped artifact acceptance unverified
- **Location:** [.github/workflows/release-build.yml:90](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/.github/workflows/release-build.yml#L90); [installer.iss:1](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/installer.iss#L1); [docs/UPDATES.md:1](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/docs/UPDATES.md#L1).
- **Evidence:** The workflow supports optional signing/unsigned pilot artifacts; tag-driven drafts and successful packaging do not establish commercial promotion approval. Updates and rollback require coordinated database/counter handling, not simply installing an older executable.
- **Reproduction / verification:** Build from the audited commit on clean supported VMs; inspect signature and hashes; exercise upgrade, migration failure and restore-based rollback with independent counters.
- **Recommended correction:** Require verified signatures for commercial promotion, publish integrity/provenance and compatibility metadata, and enforce recovery-backed coordinated update procedures.
- **Regression tests needed:** Clean install; non-admin permissions; interrupted install; wrong architecture; previous supported version; disk full; downgrade refusal; counters on mixed versions; signature tampering.
- **Implementation complexity:** XL.

## C02 — Third-party license and artifact inventory is not demonstrated

- **Severity / impact:** Medium — commercial distribution obligations may be overlooked.
- **Evidence status:** Unverified; no infringement conclusion
- **Location:** [LICENSE:1](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/LICENSE#L1); [pharma_khaato.spec:9](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/pharma_khaato.spec#L9); [requirements.txt:3](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/requirements.txt#L3).
- **Evidence:** A project license is not a complete inventory of bundled Qt/Python/cryptography and other components. Explicit third-party notices/SBOM inclusion must be verified in the built installer; hooks may already include some material.
- **Reproduction / verification:** Extract the exact installer and inventory libraries, licenses, notices, source/offer requirements and redistribution terms.
- **Recommended correction:** Create an artifact-level SBOM/notice bundle and obtain appropriate licensing review for the chosen distribution model.
- **Regression tests needed:** Installed notice availability, dependency-to-license completeness, reproducible inventory and version update checks.
- **Implementation complexity:** M.

Review the [official Qt for Python license documentation](https://doc.qt.io/qtforpython-6/licenses.html) against the exact components and distribution model; this audit does not determine legal compliance.

## C03 — Support and disaster-recovery acceptance need measurable commitments

- **Severity / impact:** High — a shop may be unable to recover trading and reconcile funds after an incident.
- **Evidence status:** Unverified operational readiness
- **Location:** [core/support_service.py:32](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/support_service.py#L32); [core/backup_service.py:1](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/backup_service.py#L1); [core/readiness_service.py:56](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/readiness_service.py#L56).
- **Evidence:** Readiness helpers and documentation cannot establish actual restore time, acceptable data loss, backup destination resilience, escalation ownership or retention capacity. Frequent full snapshots require capacity planning.
- **Reproduction / verification:** Run a timed clean-machine recovery drill, then reconcile stock, sales, cash, customer credit and supplier balances against fixture expectations.
- **Recommended correction:** Assign support ownership, define RPO/RTO and retention/storage budgets, verify off-device protected backups, and produce redacted support bundles and incident runbooks.
- **Regression tests needed:** Lost host, disk failure/full disk, corrupt latest backup, lost key, network outage, operator error, restored pending operations and support escalation exercise.
- **Implementation complexity:** L.

## Phased implementation proposal

No implementation is authorized by this audit deliverable itself. The following is a proposed sequence, with promotion gates rather than promises based on elapsed time.

| Phase | Work / finding IDs | Owners | Indicative effort | Exit evidence |
|---|---|---|---|---|
| 0 — Freeze and establish fixtures | Pin baseline, preserve existing work, resolve release environment and pytest-qt setup, capture failing tests and disposable historical schemas | QA + release + database | 2–3 days | Reproducible local/CI environment; known failures categorized; no live-data access |
| 1 — Financial and medicine invariants | A01–A05, U04/U06, D02; authoritative quote/refund allocation, trusted shift identity, MRP and prescription policy, typed unknown outcomes | Domain/backend + clinical owner + QA | 2–4 weeks | All P0 domain probes pass desired invariants; zero-value and partial returns reconcile; no duplicate posting under fault injection |
| 2 — Recovery and authorization | D01/D04/D05/D06, S01–S04, AUTH; exclusive host ownership, schema validation, independent recovery authority, network/resource bounds | Database + security + platform | 2–4 weeks | Clean-host recovery within agreed RPO/RTO; failed restores preserve original; two-process exclusion; permission matrix and isolated LAN abuse tests |
| 3 — Schema and sustained concurrency | D03/D07, unit/history policy, cash/credit/supplier reconciliation, legacy migration review | Database + backend + QA | 3–5 weeks | Exact-money migration reconciles all fixture balances; last-unit races safe; representative load meets agreed latency budget |
| 4 — Operator and accessible UI | U01–U03/U05/U07/U08, A06 as needed; settle supported screen/DPI matrix and reference-UI acceptance | PySide6 + cashier representatives + accessibility QA | 2–3 weeks | Windows/Linux CI green; manual keyboard/screen-reader and cashier scenarios accepted; no clipped critical totals or hidden unknown states |
| 5 — Commercial package and controlled pilot | S06, C01–C03; signed artifacts, dependency/license inventory, supported OS/device matrix, update/rollback runbook | Release + security + support + business owner | 2–4 weeks plus pilot observation | Independent artifact tests, recovery rehearsal, operator training, redacted support readiness, explicit human release approval |

Estimates assume an experienced small team and overlap where dependencies permit. They are planning ranges, not a fixed-price commitment. Phase 1 and 2 gates must precede use with real trading data; schema migration work requires reconciliation before any deployment. No automated merge/deployment is proposed.

## Commercial acceptance checklist with accountable evidence

- **Financial owner:** approve rounding, discount/tax policy, cash-close rules, credit limits, refund eligibility and reconciliation tolerances (money totals should reconcile exactly under the specified representation).
- **Clinical owner:** approve expiry-day semantics, malformed/quarantined/returned stock policy, FEFO exceptions, prescription verification and recall/traceability requirements. Jurisdiction-specific legal requirements remain to be established by qualified reviewers.
- **QA owner:** sign off multi-counter races, unknown outcomes, Windows/Linux DPI, supported printers/scanners, language/fonts, accessibility and long-running operation.
- **Security owner:** approve role/session/offboarding matrix, host/counter threat model, recovery authority, ACLs, dependency findings and sensitive-data handling.
- **Release owner:** verify signature, provenance, notices, install/update/rollback and exact shipped artifact version. Installer fallback version versus application version should also be aligned, even if the normal build supplies the correct version explicitly.
- **Support owner:** demonstrate off-device restore and reconciliation, publish supported versions/OS/devices and response/escalation process, monitor backup failures and capacity.

A pilot should use controlled scope, verified recoverability, named support coverage, daily reconciliation and explicit stop conditions for money/stock mismatch, authorization failure, unresolved operation outcomes or failed backups. Passing CI is necessary but insufficient. A claim of production readiness requires the evidence and human approvals above.
