# Financial storage and upgrade policy

Migration 027 adds authoritative integer companions for monetary columns. Posted ledger amounts use 100 units per rupee. Catalog/cost prices use 10,000 units per rupee; historical divided unit prices and return merchandise-allocation values retain 100,000,000 units per rupee. Supplier ledgers already use paisa. The scale for every column is defined in `core/financial_storage.py`.

Existing major-unit columns remain normalized compatibility projections for the desktop/LAN API. Database triggers maintain the integer representation on every supported write and reject inconsistent direct updates. Ledger aggregates sum integer columns before converting at the display boundary. The compatibility columns are deliberately retained to avoid a destructive, unreviewable table rewrite; application queries must never reintroduce binary floating-point ledger sums.

The conversion uses Decimal half-up rounding. Genuine historical sub-paisa ledger values stop migration with an error; only negligible binary representation noise is normalized. Operators must reconcile ambiguous historical values on a copy using original receipts and owner-approved correction records. Do not edit a live database to force an upgrade. Product/cost precision follows the documented four-place policy. `Money_Migration_Evidence` records counts, scales, totals and representation changes; it does not guess whether old receipts were financially correct.

Migrations are checksummed. Startup validates the declared schema before adopting checksums for an old store; altered migration content, missing objects, incompatible columns, missing foreign keys/unique/CHECK constraints and unknown versions are rejected. A failed upgrade retains a pre-migration backup. A rollback uses a matching application version plus its pre-upgrade backup; installing an older binary against a newer database is refused.

Run the read-only copy check:

```bash
python scripts/financial_reconciliation.py /path/to/copied-backup.sqlite --output reconciliation.json
```

The checker reports integer/projection consistency, product versus batch stock, refund/quantity caps, supplier invoice/return totals, closed-cash reconciliation, credit-ledger reconciliation and legacy conversion-review requirements. It returns nonzero for discrepancies or required historical review. It never repairs data. Review reports locally because identifiers and financial amounts are business data.

Counter concurrency is supported through one authoritative host. The host process owns the SQLite store; multiple desktop processes must not open it independently, and the live file must never be placed on a network share. The in-process database guard retains conservative serialization. The supplied benchmark measures local service work, not network latency, disk-failure behavior or physical-counter acceptance.

Prescription-required products currently fail closed at authoritative checkout and before cart insertion. There is no override checkbox or client-supplied claim of verification. A pharmacy-approved verification process is required before enabling such sales; this safe default is not jurisdictional certification.

Base-unit and strip/box conversion changes are refused after any batch has been received, including zero-stock historical batches. Use a separate product record for a different physical pack definition; historical receipts retain their original unit/price snapshots.
