# Database Schema & Migrations

Engine: embedded SQLite in WAL mode. Schema lives in `schema_sqlite.sql`
(fresh installs) plus numbered migrations applied idempotently at startup.

## Core Tables

| Table | Purpose |
|---|---|
| `Employee` | Staff accounts; password column holds versioned `pbkdf2:sha256:<iterations>$salt$hash` (600,000 iterations for new hashes) |
| `Customers` | PK is the CNIC, stored as **13 bare digits** (normalized) |
| `Supplier` | Supplier master |
| `Products` | Catalog; aggregate `stock_quantity` mirrors sum of batch quantities |
| `Batch` | Per-batch stock with expiry — drives FEFO allocation |
| `Purchase` / `Sales_details` | Sale headers and per-batch line items |
| `Receipt` | One row per sale; `printing_date` anchors debt aging |
| `Customer_Khatoo` | Credit ledger rows (`amount_paid`, `amount_due`) |
| `Login_Lockout` | Persistent brute-force counters (migration 009) |
| `product_fts` | FTS5 index over product names/formulas (migration 008) |

## Identity Normalization (critical)

CNICs are stored **without dashes**: `1234567890123`.
`customer_service.validate_cnic()` performs this normalization; checkout,
registration, and every lookup share it. Migration `010_normalize_cnic.sql`
rewrote legacy dashed rows.

## Migrations

Applied in filename order by `core.migration_manager.MigrationManager`;
applied versions recorded in `schema_migrations`. To add schema changes,
append `NNN_description.sql` — never edit applied migrations.

## Money Handling

Monetary values are computed in Python with `Decimal` (ROUND_HALF_UP).
SQLite stores them as TEXT via registered adapters — always sort/filter with
`CAST(col AS NUMERIC)` and never do arithmetic in SQL.
