# Database Schema & Migrations

Engine: embedded SQLite in WAL mode. The **base** schema for a new database is
`schema_sqlite.sql`. Numbered migrations in `migrations/` are then applied in
filename order and the applied list is recorded in `schema_migrations`.

Two facts matter before editing either file:

* **The base file is load-bearing.** Migration
  `012_credit_payments_and_perf.sql` indexes `Products.brand_name`, a column the
  base file creates and no migration adds, so the catalog cannot build a
  database from nothing. Keep the base file ahead of the catalog, never behind.
* **Replayed statements are expected, other failures are not.** Because the
  base file is a snapshot of the current schema, replaying the catalog over it
  re-declares objects that already exist. A statement failing with
  `duplicate column` or `already exists` is tolerated and logged at warning
  level; every other error stops the migration. `tests/test_schema_parity.py`
  asserts that the fresh path applies every migration, that only additive
  collisions are tolerated, that walk-in customers and default settings are
  seeded, and that a shop sitting at an older migration head upgrades to
  exactly the schema a new shop gets.

Converting the catalog so that migrations alone can build a database is planned
for 3.0; it cannot be done by renumbering applied migrations on live shops.

## Core Tables

| Table | Purpose |
|---|---|
| `Employee` | Staff accounts; password column holds versioned `pbkdf2:sha256:<iterations>$salt$hash` (600,000 iterations for new hashes) |
| `Customers` | PK is the CNIC, stored as **13 bare digits** (normalized); `WALKIN` and `GUEST_WALK_IN` are seeded for counter sales |
| `Supplier` | Supplier master |
| `Products` | Catalog; aggregate `stock_quantity` mirrors the sum of batch quantities |
| `Batch` | Per-batch stock with expiry — drives FEFO allocation |
| `Purchase` / `Sales_details` | Sale headers and per-batch line items |
| `Receipt` | One row per sale; `printing_date` anchors debt aging |
| `Receipt_Snapshot` | Immutable saved receipt text, so a reprint cannot change history |
| `Customer_Khatoo` | Credit ledger rows (`amount_paid`, `amount_due`) |
| `Credit_Payment` / `Credit_Payment_Reversal` | Account repayments and their audit reversals |
| `Cash_Register_Session` / `Cash_Movement` | Per-counter shifts and drawer entries |
| `Checkout_Request` | Checkout idempotency: fingerprint, status, resulting `purchase_id` |
| `Login_Lockout` | Persistent brute-force counters (migration 009) |
| `product_fts` | FTS5 index over product names/formulas (migration 008) |

## Identity Normalization (critical)

CNICs are stored **without dashes**: `1234567890123`.
`customer_service.validate_cnic()` performs this normalization; checkout,
registration, and every lookup share it. Migration `010_normalize_cnic.sql`
rewrote legacy dashed rows.

## Money Handling

`core/money.py` is the single quantizer: quantum `Decimal("0.01")`, rounding
`ROUND_HALF_UP`.

**Representation.** Monetary columns are SQLite `REAL`, written only as values
already quantized to two decimal places, so the stored magnitude is exact for
the amounts a pharmacy handles. Every service-level helper
(`reports_service._money`, `cash_session_service._money`,
`receipt_service._money`, `return_service._money`) delegates to or shares that
quantum, so two subsystems cannot disagree by a cent.

**Aggregates are re-quantized.** `SUM()` over `REAL` columns is a float
aggregate. Reports, drawer reconciliation and credit balances quantize the
result before it drives a decision;
`tests/test_money_and_audit_integrity.py` proves that a 3,000-line drift case
collapses back to the exact total.

**Rules**

1. Quantize at the boundary — nothing reaches the database, a receipt, a report
   or a cash count without passing through `core.money`.
2. Never compare money floats for equality; compare quantized `Decimal` values.
3. `manager_approval` discount authority is stored in minor units, not floats.

**Supplier exception.** The supplier subsystem (migration `025`) stores
`Supplier_Invoice.total_minor`, `Supplier_Payment.amount_minor` and
`Supplier_Return.credit_minor` as **integer minor units** (paisa) and carries no
float at all.

**Deliberate limitation.** The sale, credit, cash and refund columns still store
`REAL` rather than minor units. Converting them is a destructive schema change
that must backfill and verify every historical row, so it is staged for 3.0 and
is not performed in place on a live shop database.

## Migrations

Applied in filename order by `core.migration_manager.MigrationManager`; applied
versions recorded in `schema_migrations`. A real upgrade creates a verified
`quick_check` backup before its first pending change. To add schema changes,
append `NNN_description.sql` — never edit an applied migration.
