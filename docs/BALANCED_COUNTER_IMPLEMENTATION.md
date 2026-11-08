# Balanced Counter UI implementation — review notes

Scope: **Pharma-Khaato v2.4.2**, PySide6 / Qt native desktop, existing MVC/domain/SQLite/secure-LAN stack. This is a staged UI change intended for operator validation, **not** an approved pharmacy release.

## Implemented on this branch

| Workflow | Change | Safety boundary |
| --- | --- | --- |
| Application shell | Navy sidebar with readable active state, workspace header displaying task/user/shift | Same `AppRouter`, screen permissions and `SessionState`; no backend refactor |
| Sales | Search-first POS, dedicated Customer/Hold/Resume quick actions and cart count | Current scanner queue, held-sale identity, F1–F12 shortcuts and checkout request tokens retained |
| Payments | Five checked, accessible tender tiles; F4 still cycles a hidden authoritative selection combo | Tiles disabled during unresolved checkout; existing `POSController` handles transactions |
| Checkout display | Selected-lot expiry preview and totals-only discount/cash updates | Expiry is **not** FEFO allocation proof; backend lot/stock validation remains decisive |
| Owner operations | Reports shortcuts for stock alerts, credit, shifts, backups | Navigation uses existing `get_allowed_screens()` checks and actual screens |
| Display | Standard/Compact density stored as `display_density` setting; text scale unchanged | No automatic switch to reduced font size; retain 900×600 minimum |
| Reliability | Header separately displays unknown shift status instead of implying an open/closed shift | Underlying cashier cash-shift checks unchanged |

## Current keyboard mapping (do not label from artwork)

F1 medicine search; F2 customer; F3 discount; F4 tender; F5 hold; F6 resume; F10/F12 complete; Ctrl+Delete clear sale; Alt+1…Alt+8 top-level navigation. Do not create duplicate shortcuts while migrating visual controls.

## Visual and workflow acceptance tests before merge

1. **1366×768 Windows cashier:** scan several medicines rapidly, keyboard add/select unit, customer lookup, cash/card/credit payment selection, change/discount, hold/resume, receipt reprint.
2. **900×600 / 1024×768:** search and primary button remain reachable; summary can scroll while total and Complete Sale stay visible; quick actions shorten without hiding help.
3. **DPI and contrast:** Windows 100/125/150%, app text 1.0/1.25/1.5, both themes, both density choices. No clipped table editors or settings form rows.
4. **Pending sale:** disconnect main LAN host after submitting a sale. Tender/quantity/customer controls remain locked; retries reuse the stored request identity; receipt failure never triggers a second sale.
5. **Inventory:** expired/blocked lot remains unsellable; expiry shown in cart is only a preview, and final checkout can use different FEFO lots. Check correct behavior with multiple batches and same product.
6. **Operational controls:** role-based visible navigation and backend permission restrictions still agree. Open/closed/unavailable shift labels must be clear.
7. **Hardware acceptance:** scanner termination, duplicate barcode prefixes, printer disconnect and reprint on actual 58/80mm printers, and physical cash reconciliation.
8. **Release gates:** cross-platform Qt smoke, business integration suite, installed package checks, restore on independent computer and pharmacy owner sign-off.

## Deferred by design

Do not replace domain services, migrate to PostgreSQL, turn SQLite into a network-shared database, add unvalidated payments, or treat receipt artwork as accounting truth. A true dedicated owner analytics dashboard, virtualized large credit/cart tables, verified support/legal compliance and physical hardware certification remain future gated work. Do not mark this branch as stable or 100% market ready.

## CI commands

```bash
python -m compileall -q main.py controllers core models ui scripts
python scripts/ui_audit.py
QT_QPA_PLATFORM=offscreen python -m pytest -q
python scripts/test_gui_auto.py
```

If the full suite passes, still test physical hardware and shop operations separately. Automated tests alone cannot certify safe pharmacy deployment.
