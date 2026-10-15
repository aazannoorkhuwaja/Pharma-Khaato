# AGENTS.md

Pharma Khaato is treated as a deployable pharmacy product, not a demo project. Agent work must preserve real-world financial, inventory, audit, backup and checkout correctness before visual polish.

## Product roles

### 1. Product & UX Lead
Owns operator workflows and product feel.

Responsibilities:
- cashier-first POS flow, keyboard/scanner ergonomics and zero-surprise dialogs
- pharmacy-owner workflows for stock, credit, returns, reports and settings
- consistent terminology, empty/loading/error states, accessibility and responsive layout
- remove developer/project wording from customer-facing surfaces
- validate that routine tasks do not expose internal database IDs

Acceptance:
- every major workflow is understandable without developer knowledge
- no blocking work is added to the Qt UI thread
- visual changes keep the existing design tokens and responsive layout rules

### 2. Desktop Engineering Lead
Owns PySide6 application shell and interaction reliability.

Responsibilities:
- startup/login/logout/navigation lifecycle
- background task orchestration and stale-result protection
- single-instance behavior, window/application metadata and OS integration
- printer/scanner integration boundaries and recoverable failures
- application responsiveness on ordinary pharmacy hardware

Acceptance:
- interactive actions do not freeze the GUI
- sign-in/sign-out can be repeated safely
- the app cannot accidentally start competing sessions against the same local data store

### 3. Data & Financial Integrity Lead
Owns correctness of persisted business facts.

Responsibilities:
- transactional sale/return/credit/cash workflows
- checkout idempotency and crash retry behavior
- FEFO/batch/expiry correctness
- tender-aware cash reconciliation
- immutable historical sale facts and auditability
- safe migrations and SQLite indexes for real query paths

Acceptance:
- no duplicate charge/stock deduction on checkout retry
- digital tenders never alter physical drawer cash
- returns cannot exceed sold quantities
- credit balances cannot silently drift
- migrations are ordered, idempotent where appropriate, and backed up before risky changes

### 4. Reliability & Support Lead
Owns recovery, diagnostics and field support.

Responsibilities:
- automatic/manual backups and restore safety
- health/readiness checks
- rotating logs and crash evidence
- privacy-conscious support bundles that exclude the live business database by default
- disk-space and corruption handling

Acceptance:
- a pharmacy can recover from ordinary workstation failure without source-code access
- support can diagnose a workstation without automatically receiving customer/business records

### 5. Release & Packaging Lead
Owns installable artifacts.

Responsibilities:
- PyInstaller specification and hidden imports
- Windows installer and Linux desktop/install integration
- version consistency, release checksums and packaged-app smoke tests
- clean install, upgrade and uninstall behavior
- application data must remain outside the executable/install directory

Acceptance:
- an operator installs and launches without Python, pip, git or a terminal
- user data survives application upgrades/uninstall unless explicitly removed by the operator
- release artifacts are reproducible enough to identify by version + checksum

### 6. QA / Launch Gate Lead
Owns evidence that the integrated product is shippable.

Responsibilities:
- regression tests for every fixed production bug
- fresh-database migration checks
- isolated demo business-flow verification
- offscreen major-screen smoke tests
- PR/full matrix on supported Windows/Linux + Python runtimes
- manual hardware checklist for printer/scanner/cash drawer

Acceptance:
- no launch candidate is approved from a red CI head
- failures must be traced to the exact current commit
- hardware-dependent claims require real-device acceptance, not assumptions

### 7. Repo & Documentation Lead
Owns the public engineering surface.

Responsibilities:
- product-first README, changelog, support/security/deployment docs
- remove obsolete hotfix/test artifacts from the repository root
- keep developer architecture below operator/product documentation
- maintain concise release notes and known limitations

Acceptance:
- opening the repository should feel like the engineering home of shipped software, not a university submission folder

## Integration owner: Release Lead

The Release Lead integrates all role outputs and is the only role allowed to call a build a launch candidate.

Integration order:
1. data/financial correctness
2. runtime/reliability
3. operator workflow/UX
4. packaging
5. QA gates
6. repository/release documentation

Never trade correctness for a prettier demo.

## Branch and release rules

- `develop-ui` is the active engineering branch.
- `launch-candidate` is a reviewable history-connected snapshot used for the PR into `main`.
- `main` must not be changed or merged without explicit owner approval.
- Every product bug fix gets a regression test when practical.
- Do not bypass failing CI by weakening tests unless the old test is demonstrably protecting obsolete behavior.
- Do not place the live SQLite database on a network share.
- Do not include demo/reset operations in the production data directory.
- Do not expose secrets, passwords, full databases or customer records in diagnostics/support bundles.

## Agent skills

### Issue tracker
GitHub Issues (uses `gh` CLI against `aazannoorkhuwaja/Pharma-Khaato`). See `docs/agents/issue-tracker.md`.

### Triage labels
Canonical 5-role triage label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs
Single-context layout (`CONTEXT.md` + `docs/adr/` at repo root). See `docs/agents/domain.md`.

## Execution rule

- Auto-continue across phases when the requested change is safe and the acceptance criteria are clear.
- If work is blocked only by physical hardware, OS permissions, credentials or another external action, keep progressing on independent work and leave an exact guided step for the owner.
