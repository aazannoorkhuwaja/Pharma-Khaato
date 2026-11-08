# Pharma-Khaato: UI design decision and commercial readiness plan

Status: **engineering plan, not a release sign-off**. Baseline: `main` commit `282a5be` (v2.4.2). Target: one pharmacy, offline primary counter, optional secure shop-LAN counters. Do not reset or migrate a real pharmacy merely to apply a UI design.

## Design direction

Adopt the cashier's preferred reference: **navy sidebar + porcelain-white content + emerald primary actions**. Continue using PySide6 / Qt widgets and the existing `ui/theme` tokens, shared components, MVC controllers, and Qt-free core services. Preserve keyboard-first search, an immediately visible amount due and final action, a verified current shift, customer identity when credit is selected, and a durable pending-checkout identity. The mockup is a **visual target, not executable product requirements or accurate medicine/accounting data**.

**Workspaces**:
- **Cashier**: New Sale is the landing page. Medicine/scan search, selected product results, cart, customer lookup, total, tender, cash received/change and safe checkout are visible. Hold/Recall, reprint and returns are one action away.
- **Owner**: an operational dashboard with expiring stock, pending supplier dues, unsettled customer credit, shift discrepancies and backup health. Do not use charts instead of actionable lists.
- **Stock clerk**: catalog, receiving, batches, counted adjustments and alerts. Show medicine/pack/batch context where it changes an inventory decision; do not expose raw database IDs as routine labels.

### Component policies

- Navigation: task-first labels; reflect permissions; do not equate hiding controls with authorization.
- Tables: `QTableView` / `QAbstractTableModel` + pagination/model-backed search for high-volume records; use `QTableWidget` only for small, bounded editable tables. Use consistent money formatting and right alignment.
- Color: semantic tokens; green = success/primary, amber = warning, red = blocked/danger. No status communicated by color alone. Expired or quarantined stock must be **blocked by core service**, not just badged.
- Inputs: explicit field labels and accessible names, correct tab order, visible keyboard focus, descriptive errors, disabled states that explain why. Avoid mandatory CNIC/phone for walk-ins.
- Layout: verify 900x600 minimum; 1024x768; 1366x768; 1920x1080; Windows DPI 100/125/150%; Qt interface scale 1.0/1.25/1.5; light/dark. Keep checkout and payment totals visible or directly accessible and do not clip fields.
- Keyboard: preserve current F1 Search, F2 Customer, F3 Discount, F4 Tender, F5 Hold, F6 Recall, F10/F12 Checkout while transitioning. The mockup's F2/F4 labels conflict with the existing implementation. Print an accurate Help/Shortcuts legend.
- Receipt: show **sale committed** separately from **receipt printed**. On spooler/USB failure, permit reprint of the same sale and never suggest another checkout.
- Sensitive data: avoid displaying customer CNIC, passwords, private customer information, backend keys, or records on shared counters without task justification. Logs/support bundles must redact them.

### Present gaps found in the code and documentation

1. The POS builds `QComboBox` editors for each cart row in `refresh_cart_display()` and previously refreshed the full table for every discount/cash spinner edit. The pilot routes these monetary edits to a small totals-only refresh. **Native GUI tests must confirm signal behavior and focus retention.**
2. The cart had a hidden raw Batch ID column rather than user-facing expiry information. The pilot uses an expiry **preview** where product lookup supplies an expiry date. This is *not* a final FEFO allocation: final batch/price/expiry must remain authoritative in `core.pos_service`.
3. Some business screens use eager `QTableWidget` population and large modules (`pos_screen.py`, `inventory_screen.py`, `settings_screen.py`). Extract reusable cart/payment components and models gradually; do not simultaneously rewrite transaction code.
4. Monetary computations already use `Decimal` in important core paths, but persistence and certain result interfaces still use Python floats/SQLite `REAL`. Audit all calculation/write/read/report paths before a controlled future migration to integer paisa. Never silently recast existing records: preserve original values and verify reconciliation.
5. The coarse `_DB_GATE` in `core/db_engine.py` provides predictable serialization but can constrain throughput on multiple counters. Profile on shop hardware before adjusting locking or transaction scope.
6. `docs/AUDIT_REPORT.md` contains historical Tkinter-era details, and `docs/TESTING.md` refers to `scripts/benchmark.py` absent from the current tree. Treat historical reports as historical; maintain current command lists separately.
7. The repository has cross-platform automated build/test workflows but the physical shop acceptance checklist is still pending. CI green is **not** proof of printer, barcode scanner, durable power-loss recovery or user acceptance.
8. Sample UI artwork contains inconsistent totals, dates, and expiry statuses. Do **not** copy those figures or unsafe actions into production test fixtures or public demos.

## End-to-end screen inventory and acceptance criteria

| Area | Cashier/operator journey | Edge cases and acceptance gate |
| --- | --- | --- |
| First run / login | Create owner, sign in, setup checklist, role-based home | Existing data preserved; failed login lockout; no default passwords; restart survives |
| POS search | Search name/generic/barcode, select pack or batch, add/edit cart | Scanner terminator, rapid scans, leading zeros, duplicate items, no results, low stock, expired/blocked lot |
| Checkout | Review price/tax/discount, choose tender, commit | No duplicate on retry; changed price/tax; missing customer for credit; manager discount approval; cash shortfall; no shift |
| Receipt | Print after commit, preview/reprint saved historical receipt | Printer disconnected/empty, Unicode, 58/80 mm, long medicine names, no second sale |
| Hold/recall | Save cart, exit, recall and complete | Interrupted app, stale stock, changed prices, different cashier, pending checkout priority |
| Customers / Khatoo | Find by name/phone, create optional-contact customer, sell on credit, collect part/full | Duplicate names, privacy, balance limits, same payment retry, repayment reversal, opening balances |
| Inventory | Create product, units and barcodes, stock count, warnings | Strips/tablets/boxes, fractional pack mismatch, negative stock, blocked/recalled items, duplicate barcodes |
| Batch / expiry | Inspect lots by expiry, block/quarantine and adjust | Expiry today/month precision, FEFO with differing lot prices, stale lot and concurrent last stock |
| Receiving / suppliers | Receive invoice, free units, credit/payment, returns | Duplicate invoice, price mismatch, ambiguous units, over-return, recovery after lost reply |
| Returns / refunds | Find original bill, return partial quantity, choose refund route | Repeat request, original historic price, expired/damaged stock quarantine, credit customer settlement |
| Shift / cash | Open shift, cash movements, close and count | Digital tender excluded from drawer, shortage/overage acknowledgement, cross-counter isolation, refund after closure |
| Reports | Daily sales vs returns, profit, tax, dues and stock | Refund dates, date boundaries, precision, totals reconcile to underlying ledger, permission scope |
| Settings / staff | Role access, pricing/tax/receipt/backup settings | Changed password revokes LAN session; sensitive operations require backend permission |
| Backup / recovery | Make external copy, restore on spare machine | WAL-safe snapshot, integrity check, changed schema, disk full, interrupted restore, actual restoration rehearsal |
| LAN counters | Trusted certificate, operator login and main-shop server | Main server loss, cert expiry/rotation, duplicate requests, two simultaneous last-item sales, no fallback local shop |
| Installation/update | Install, upgrade, rollback/recover and uninstall | Data stays outside install directory, signatures/checksums, no deleting shop data, native printer and scanner tests |
| Help / support | Accessible contextual help, support bundle, operator quick start | Never leak secrets or raw customer records into routine diagnostics |

## Proposed safe implementation sequence

**Gate 0 — Protect existing customers.** Pin a known green revision; create safety copy of a disposable test shop; run Linux/Windows Qt smoke and backend suite. Do not change live data here.

**Gate 1 — Cashier design pilot.** Apply selected expiry preview, totals-only monetary update, regression guards, accurate shortcuts, stable receipt/shift statuses. Validate focus, no clipping and checkout safety at multiple screen sizes. No business rule change.

**Gate 2 — Role workspaces.** Use the same shell and theme. Add task-first cashier/owner navigation and conditional information panels; preserve all RBAC service guards.

**Gate 3 — Data/financial audit.** Catalog every `REAL` and float usage, define minor-unit conversion strategy, migration rollback and backfill reconciliation on copied shop data. Separate cash movement, payment tender and customer credit semantics.

**Gate 4 — Operational robustness.** Test interrupted checkout, printer failure, offline LAN, last-unit contention, mixed pack lots, returns, partial repayments, expiry-day edge and cash discrepancy. Replace eager tables incrementally using model-backed views.

**Gate 5 — Real device acceptance.** Windows 10/11, Ubuntu 22/24, 1366x768 baseline, 100/125/150% DPI, scanner and 58/80mm printer, 10 uncoached bills, cash opening/closing, backup and restore on spare workstation. Record device, tester, result and evidence.

**Gate 6 — Legal/commercial release review.** Validate locally applicable pharmacy operations, medicine-sale record retention, prescription handling, tax/fiscal requirements, privacy/backup handling, licensing and product support expectations with qualified advisers. Complete installer verification, signed release where feasible, clear update/rollback, support workflow and owner sign-off.

## Explicit release decision

**Market ready is not a numeric software-test percentage.** It requires complete end-to-end acceptance, zero unresolved blocking data-integrity failures, known supported hardware, verified recovery, legal review and a shop-owner sign-off. Until then, label the app an engineering/pilot build, not certified production pharmacy software.

## Reference implementation constraints

Retain the proven local SQLite + WAL path and Python/PySide6 services. Do not move to FastAPI, PostgreSQL, React, Electron or a cloud backend merely for presentation. The existing authenticated TLS LAN transport is adequate as a starting point; replace it only after measurable needs and associated migration/security tests.
