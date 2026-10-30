# POS readiness review — 2.4.2

Scope: single-pharmacy desktop billing on Windows, with Ubuntu owner testing and a receipt printer; barcode hardware later. No claim of regulatory certification or clinical prescribing support.

Established POS products include inventory, staff access, returns and checkout workflows: [Shopify feature overview](https://www.shopify.com/pos/features), [staff permissions](https://help.shopify.com/en/manual/your-account/users/roles/permissions/pos-permissions), [returns](https://help.shopify.com/en/manual/sell-in-person/shopify-pos/order-management/complete-refund-orders?locale=en). Those are a baseline, not a reason to add unrelated e-commerce features to a pharmacy counter.

| Workflow | Existing implementation / verification |
|---|---|
| Cash, wallet and credit bills; retry without duplicate stock deduction | Transactional checkout, durable idempotency keys, immutable receipt snapshots; financial-integrity and checkout tests |
| Medicine stock, packs, lots, expiry, unavailable stock | Base units, FEFO allocation, blocked/expired batch rejection; pharmacy-units and inventory tests |
| Supplier invoice, free units, payments and returns | Atomic stock/ledger transaction and recoverable operation identity; supplier recovery tests |
| Customer dues and collections | Name-first identity, optional phone, credit limits, payment allocation and replay safety; customer-credit tests |
| Cash count and closing summary | Counter-specific shifts, digital-tender exclusion, count acknowledgement; cash and recording-review tests |
| Refunds and reprints | Return limits, original recorded prices, saved receipts; returns and receipt recovery tests |
| Staff access | Backend permissions, owner-controlled accounts, authentication and revocation tests |
| Backups and recovery | External backup destination, staged restore, migration backup and support bundles; recovery and support tests |
| Offline desktop and multiple counters | Local SQLite; separate authenticated TLS service for additional counters, never shared SQLite files; LAN tests require socket-capable environment |
| Installation and updates | Separate app/data directories; Windows and Linux install, upgrade and packaged smoke workflows |

## Second recording corrections

All eight observed defects have targeted changes: scrolling Settings and sidebar layouts, full supplier money columns, larger invoice entry area, live semantic text colours, synchronized theme selection, two-line customer suggestions, correctly sized unit editors and separated account/navigation areas. Expired lots now say Expired. Legacy NULL contact-field search and stale invoice unit choices also receive regression coverage.

Local real-stylesheet checks cover both themes at 100%, 125% and 150%. CI must additionally pass on Windows/Linux and Python 3.12/3.14 at the final commit. Physical printing, owner stock/cash reconciliation and clean real-shop setup remain field acceptance steps; see [Shop Trial](SHOP_TRIAL.md).

The recording contains old test records. No packaging change deletes or resets existing business data. The package specification includes code/schema/migrations, not a live business database. A clean install and existing-data upgrade are separate acceptance cases.
