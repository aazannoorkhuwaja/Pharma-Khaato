# Pharma-Khaato v2.3.1 — HCI/SDE + Setup UI Delivery Notes

## Product focus

v2.3.1 builds on the responsive v2.2 interface and focuses on learnability for non-technical pharmacy staff. The backend/MVC contracts are preserved; the visible language, workflow cues, status messages, and error-prevention behavior are improved.

## HCI improvements

- Main navigation is now task-first: **New Sale, Customers, Customer Credit, Stock & Products, Shift & Cash, Reports, Settings**.
- Primary actions use short verb-first labels such as **Complete Sale, Add Stock, Resume Sale, Record Payment, Start Cash Shift**.
- POS wording was shortened and the previous multi-line `POS Billing Counter` title was replaced with `New Sale`.
- Duplicate shortcut clutter was reduced; keyboard accelerators remain available for experienced operators.
- Empty states tell the user what to do next instead of describing system state.
- Technical/system terminology was removed from routine screens wherever it did not help complete a task.
- Technical diagnostics are now hidden behind **Show Technical Details** (progressive disclosure).
- Non-cash payment methods disable the Cash received input (error prevention).
- Roles are displayed as **Cashier, Pharmacist, Administrator**.
- Inventory explains earliest-expiry behavior in plain language while keeping FEFO as an internal implementation rule.
- User-facing error messages are shorter and provide the next useful action where possible.

## SDE improvements

- Added `ui/ux_copy.py` as a centralized product-language layer.
- Friendly labels are explicitly separated from stable backend/domain values.
- Examples: `Customer Credit` → `Khatoo Credit`, `Cashier` → `Salesman`, `Administrator` → `Admin`, `Cash In` → `CASH_IN`.
- No database migration is required and historical records/permissions remain compatible.
- Added `tests/test_hci_copy_and_domain_separation.py` to guard terminology and presentation/domain separation.


## First-run setup hotfix

- Setup now inherits the global live theme; the stale dark section background on a light setup screen is removed.
- The form is centered and capped at 960 logical pixels instead of stretching across maximised windows.
- Fields reflow between two columns and one column based on available width.
- Setup cards scroll only when needed; the final action remains visible and never overlays fields.
- Required/optional labels, examples, accessible names, focus behavior, and validation messages were improved.

## Responsive design retained

- Full/compact/mini adaptive sidebar.
- DPI-aware controls and 1.0x/1.25x/1.5x interface scaling.
- Flexible POS/payment, customer, stock, and administration panels.
- Scalable table rows and scroll-safe wide data.
- Monitor-aware/resizable dialogs.
- Responsive report KPIs and compact POS shortcut badges.

## Verification

- Automated pytest suite: **71/71 passed**.
- MVC architecture checks: passed.
- HCI copy/domain separation checks: passed.
- Responsive UI source checks: passed.
- Existing authentication, POS, credit, stock, reports, cash-shift, backup, and security tests: passed.

## One-file UI test launcher

`PharmaKhaato-v2.3.1-Universal-Test.py` is the same test file for Windows and Linux. It embeds the runtime application, creates a private versioned virtual environment, installs the Python-compatible PySide6 dependency on first launch, keeps test data isolated, and opens the GUI.

Python 3.10+ is required. The first launch needs internet access for PySide6 installation. Native production binaries remain OS-specific because Qt ships native Windows/Linux libraries.

For the usability rationale and large-system rules, see `docs/HCI_SDE_USABILITY_REVIEW.md`.
