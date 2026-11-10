# Supplied UI reference implementation

Source: `Pharma-Khaato-UI-Preview-Light.zip`, its eleven high-fidelity images,
interactive prototype and design-system notes. Implementation branch:
`ui/reference-replica`. The source images remain local reference assets; they
are not rendered as the application interface.

## Screen mapping

| Reference | Native implementation |
| --- | --- |
| Billing, alternate billing | Search/action toolbar, cart with quantity controls and removal, customer/results panels, invoice summary, five tender tiles, pinned checkout on short screens |
| Owner dashboard, reports | Existing Reports workspace with eight actual financial metrics, seven-day net-sales trend, tender distribution and operational links |
| Stock and products | Catalog with selected medicine details and stock/edit actions |
| Batches and expiry | Dedicated Batches & Expiry tab with search, supplier/expiry/condition filters, pagination, selected-batch details, actual counts and existing stock-correction action |
| Purchase receiving | Supplier invoice dialog with receiving lines, live GRN total, payment source and balance summary; existing atomic receipt workflow |
| Customer credit | Account table with selected customer balance and actual statement alongside |
| Returns and refunds | Original-sale table beside refund form, original tender and live estimated refund; stacked layout on small screens |
| Shift and cash | Actual drawer summary alongside cash movement history |
| Settings and staff | Two-column profile/business settings on wide screens, existing staff and recovery tabs |

Navy `#152843`, canvas `#F3F7FC`, emerald `#089B61`, pale green `#E5F7EB`,
ink `#10203C`, muted text `#66768A`, and borders `#D9E2ED` come from the
reference pack. Native vector icons, keyboard focus, theme switching and
responsive layouts remain supported. Optional tools are in the sidebar's
Shop Tools menu, with role visibility preserved.

## Deliberate differences from the artwork

This is a native functional interpretation, not a pixel-identical reproduction
of every illustration. The images show fabricated numbers and conflicting
shortcuts. Real tax, balances, expiry, shift state and receipt availability
remain authoritative. Product expiry and available quantity appear under its
name; internal batch IDs are not exposed. The owner overview shares Reports;
batch/receiving/staff workflows retain their existing tabs and dialogs rather
than pretending that all 25 prototype pages are new production screens.

Existing F1–F6 and F10/F12 shortcuts remain active. The checkout request,
FEFO, permissions, cash reconciliation, receipt, refund and backup services
were not rewritten. A read-only batch-browser query was added through the model/controller layers and LAN inventory-read permission. Charts use asynchronous existing report-controller reads.
Medicine and customer previews invalidate older requests on selection changes.

## Review and testing

Run the actual local app with `python3 main.py`. It uses the normal application
data location. Screenshots generated during development use isolated new
practice databases under ignored `artifacts/` directories.

Native captures: `artifacts/reference-review/`. The populated subfolder contains
all eight main screens plus populated batch, compact batch and receiving examples. The matrix
covers eight screens at ten size/theme/density/text-scale combinations, including
910×480 and 855×440 logical desktops. This checks geometry, not pixel identity.

`tests/test_reference_ui.py` exercises tender selection and checkout locking,
quantity controls, product preview, real report data and cashier utility
permissions without requiring pytest-qt. It also verifies receiving commits stock and supplier balances together and refund previews follow selected quantities. `tests/test_batch_browser.py` checks filtering, pagination, read-only behavior and role enforcement. The full repository suite still needs
pytest-qt; it was unavailable in this environment, and downloading it failed.
Actual desktop-window, Windows DPI and printer/scanner testing remain manual.

Recreate the captures using `python3 scripts/reference_ui_review.py`, or run the
strict geometry checks using `python3 scripts/reference_ui_review.py --matrix`.
Both commands create isolated data directories and leave user data untouched.

Latest local verification: 125 targeted tests passed (including recovery and release acceptance). One legacy
pytest-qt test was deselected; another recovery-screen test could not initialize
because its qapp fixture requires the unavailable pytest-qt dependency. Source compilation, all
six UI audit checks and the 80-capture geometry matrix passed. No UI changes have
been merged into main. Publication uses the ui/reference-replica review branch.
