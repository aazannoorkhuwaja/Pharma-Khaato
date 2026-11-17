# Security audit

Audit evidence collected: 2026-11-10; reports finalized: 2026-11-11. Phase 1: analysis and documentation only.

Baseline: local `ui/reference-replica`, commit `1dd242cebae3ca792750fc8dc91f03b84a7705ec`, matching the GitHub branch at inspection. GitHub `main` was `1fc56654c5a69ae62525a13b17c6235568f6eee6`; findings target the audited branch, not an assertion that main has identical UI. No application code, live database, merge, deployment, or release changes were made.

Evidence labels: **Reproduced** = observed in a disposable database or recorded exact-commit CI; **Source-confirmed** = reachable behavior established by code inspection; **Risk** = plausible consequence requiring a targeted experiment; **Unverified** = missing acceptance evidence. Severity reflects business impact, not exploitability alone. Complexity: S = 1–2 engineering days; M = 3–5; L = 1–2 weeks; XL = multiple weeks. Estimates exclude independent acceptance, regulatory review and rollout; overlapping fixes must not simply be summed.

## Threat model and positive controls

Trust boundaries: shared counter OS account → GUI; counter → shop HTTPS service; session → role-authorized mutation; database/backup files → recovery; downloaded installer → workstation. PBKDF2 password hashing, constant-time verification, persisted lockouts, LAN method allowlisting, server-derived actor identity, TLS and parameterized SQL are present. They do not protect against every local file-level attacker. No penetration test, complete dependency advisory scan, or full secret-history scan was completed; absence of a reported secret is not a clean-history certification.

## S01 — LAN request lifecycle lacks demonstrated resource bounds

- **Severity / impact:** High risk — a counter-network peer may make the shop service unavailable.
- **Evidence status:** Risk; sandbox blocked socket experiments
- **Location:** [core/lan_service.py:285](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/lan_service.py#L285); [core/lan_service.py:297](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/lan_service.py#L297).
- **Evidence:** ThreadingHTTPServer and listener TLS wrapping need bounds before handshake/header parsing. Setting a timeout inside do_POST occurs after those stages; thread creation also needs a global limit.
- **Reproduction / verification:** In an isolated network harness hold partial TLS handshakes and slow HTTP headers while a legitimate counter requests service; measure accept latency and thread count.
- **Recommended correction:** Apply handshake/header/body deadlines before parsing, bounded concurrency and payload limits, per-peer/global rate limits, and graceful saturation responses.
- **Regression tests needed:** Slow TLS/header/body; idle connection flood; oversized body; valid client under load; shutdown with blocked clients; no unauthenticated expensive work.
- **Implementation complexity:** L.

## S02 — Authentication and session retention permit resource growth

- **Severity / impact:** Medium — unauthenticated username spraying and abandoned sessions can accumulate state.
- **Evidence status:** Source-confirmed retention pattern; exhaustion untested
- **Location:** [core/auth_service.py:46](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/auth_service.py#L46); [core/auth_service.py:94](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/auth_service.py#L94); [core/lan_service.py:151](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/lan_service.py#L151).
- **Evidence:** Lockout pruning targets expired positive lock deadlines; one-failure usernames with no lock deadline can remain. Session-associated model caches require bounded expiration, not only logout cleanup.
- **Reproduction / verification:** Attempt one failed login per unique username in a scratch service and count retained rows; create/expire sessions without logout and inspect cache size.
- **Recommended correction:** Add global/per-peer throttling, timestamps and bounded TTL cleanup for attempt/session/model state; retain only necessary audit evidence.
- **Regression tests needed:** Username spray, repeated known user attempts, idle session expiry, password reset revocation, cleanup under concurrency, bounded memory/storage.
- **Implementation complexity:** M.

## S03 — Recovery authenticates against the selected backup

- **Severity / impact:** High conditional risk — a shared-OS user who can supply a crafted backup may choose their own recovery credential.
- **Evidence status:** Source-confirmed trust decision; unauthorized live restore not attempted
- **Location:** [core/recovery_service.py:20](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/recovery_service.py#L20).
- **Evidence:** The recovery credential is checked against the user-selected database. It does not independently establish authorization from the current shop owner. A full OS administrator already controls the files; shared-counter threat models differ.
- **Reproduction / verification:** Create an independent scratch database with a known admin, select it in a disposable recovery flow, and determine whether any existing-owner proof is required.
- **Recommended correction:** Define an owner recovery authority independent of untrusted backup content: protected recovery secret, signed trusted manifest and/or enforced OS administration workflow.
- **Regression tests needed:** Foreign-shop backup, crafted admin, missing current DB, legitimate owner disaster recovery, tampered manifest, expired/revoked recovery credential.
- **Implementation complexity:** L.

## S04 — Sensitive data files rely on inherited filesystem permissions

- **Severity / impact:** High risk on shared machines — customer and financial information may be readable outside the intended account.
- **Evidence status:** Source-confirmed default permission strategy; deployed ACLs unverified
- **Location:** [core/path_manager.py:46](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/path_manager.py#L46); [core/backup_service.py:189](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/backup_service.py#L189).
- **Evidence:** Directories/files rely substantially on OS defaults; TLS private-key protection does not establish equivalent database/backup/receipt protection. Database backup encryption is not established.
- **Reproduction / verification:** Inspect mode/owner/ACL for data, WAL, SHM, receipts and backups on clean Linux/Windows installs under permissive defaults.
- **Recommended correction:** Apply least-privilege directory and file access, protect exported backups, document full-disk encryption and shared-account limitations, and define retention/redaction policy.
- **Regression tests needed:** Linux umask 022 and shared parents; Windows non-admin install ACL; external backup destination; temporary/support files; lost-device recovery.
- **Implementation complexity:** M.

## S05 — Spreadsheet exports preserve formula-capable product text

- **Severity / impact:** Medium — opening exported reports can execute spreadsheet formulas.
- **Evidence status:** Source-confirmed output; spreadsheet-specific execution untested
- **Location:** [ui/screens/reports_screen.py:394](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/reports_screen.py#L394).
- **Evidence:** Untrusted product/category strings are passed to CSV output without a formula-neutralization policy. CSV quoting alone does not neutralize formula interpretation.
- **Reproduction / verification:** Create a scratch product named =1+1, export a report, inspect the CSV and open only in a disposable spreadsheet profile.
- **Recommended correction:** Neutralize dangerous leading characters according to an explicit spreadsheet-export policy while retaining an appropriate raw-data export if required.
- **Regression tests needed:** Leading =,+,-,@, tabs and carriage returns; quoted delimiters; Unicode; ordinary negative numeric fields; Excel and LibreOffice.
- **Implementation complexity:** S.

## S06 — Dependency vulnerability and provenance gates are incomplete

- **Severity / impact:** High release risk — known-vulnerable dependency families can ship without an evaluated advisory decision.
- **Evidence status:** Source-confirmed pin and missing audit evidence; application exploitability unverified
- **Location:** [requirements.txt:3](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/requirements.txt#L3); [.github/workflows/ci.yml:17](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/.github/workflows/ci.yml#L17); [.github/workflows/release-build.yml:90](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/.github/workflows/release-build.yml#L90).
- **Evidence:** Python <3.13 release dependencies pin Qt 6.7.2. The official Qt CVE-2025-5455 advisory includes that version family; exploit conditions include assertions enabled and malformed data URLs. Receipt rendering uses plain text, so this audit does not establish a reachable exploit. pip-audit was unavailable locally; no complete transitive scan was run.
- **Reproduction / verification:** Resolve exact release wheels on supported OS/Python versions; generate an SBOM and compare advisories against binary build flags and reachable APIs.
- **Recommended correction:** Upgrade to a tested supported security patch line; lock reproducible dependency resolutions/hashes, scan artifacts, and record advisory reachability/exception decisions.
- **Regression tests needed:** Clean locked build; advisory gate; Qt rendering and packaging smoke; dependency license inventory; reproducibility and provenance verification.
- **Implementation complexity:** L.

The Qt version claim is supported by the [official Qt advisory](https://www.qt.io/blog/security-advisory-recently-discovered-issue-in-qdecodedataurl-in-qtcore-impacts-qt) and [Qt vulnerability index](https://wiki.qt.io/List_of_known_vulnerabilities_in_Qt_products). An affected dependency is not proof of application exploitability. No claim is made that these are the only advisories applicable to the release.

## Authorization acceptance gaps

Test every mutation as admin/manager/cashier, through both local and LAN adapters, with forged actor/terminal IDs and stale sessions. Explicitly define employee deactivation, active-session revocation and idle counter locking; password reset alone is not a demonstrated complete offboarding workflow. These are unresolved acceptance requirements rather than a proven remote privilege escalation. Sensitive support bundles need explicit field inspection and consent policy before external sharing.
