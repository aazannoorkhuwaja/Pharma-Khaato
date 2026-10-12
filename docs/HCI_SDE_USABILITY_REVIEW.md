# Pharma-Khaato v2.3 — HCI & SDE Usability Review

## Goal

v2.3 focuses on making the desktop application understandable to pharmacy staff who may be good at counter work but not comfortable with technical software terminology. The design keeps the fast keyboard workflow for experienced operators while making the first-use experience more self-explanatory.

The implementation applies human-computer interaction (HCI) principles together with software design engineering (SDE) rules so wording, behavior, and business logic can evolve independently.

## Product language standard

The interface now uses the user's task as the label, not the internal subsystem name.

| Previous wording | User-facing wording | Why |
|---|---|---|
| POS Billing Counter | New Sale | Describes the task the cashier wants to start |
| Khatoo Ledger | Customer Credit | Familiar outcome; local term can still exist in help/training |
| Inventory Master | Stock & Products | Concrete nouns that staff recognize |
| Cash Register | Shift & Cash | Matches the daily opening/closing workflow |
| Daily Reports | Reports | Removes unnecessary scope wording |
| System Settings | Settings | Standard desktop convention |
| Recall Sale | Resume Sale | Describes the action rather than a system concept |
| Confirm & Pay | Complete Sale | Clear end state |
| Add Batch | Add Stock | Staff think in stock intake; batch details remain in the form |
| FEFO | Earliest expiry first | Plain language in the UI; FEFO remains an internal/domain term |
| Technical Diagnostics & Runtime Health | System & Backup / Technical Details | Technical detail is progressively disclosed |

## HCI principles applied

### 1. Match the real world

Labels use pharmacy-counter concepts: Sale, Customer, Credit, Stock, Shift, Cash, Reports, Settings. Technical database, runtime, and architecture terms are not used as primary navigation language.

### 2. Recognition over recall

- Primary navigation is task-based and includes shortcuts without requiring memorization.
- POS actions use clear verbs: Find, Hold Sale, Resume Sale, Complete Sale.
- Empty states tell the user what to do next.
- Payment choices use familiar visible names while the application retains stable internal values.

### 3. Minimize cognitive load

- Long headings and duplicate shortcut instructions were reduced.
- The settings screen hides support diagnostics until the administrator explicitly opens Technical Details.
- Tables use shorter column names while retaining the data needed for the task.
- Screen subtitles explain purpose in one short sentence rather than implementation details.

### 4. Consistency and standards

- Create/add actions use `Add ...` or `Save ...` consistently.
- Destructive/exit actions use clear labels such as Sign Out and Clear Sale.
- Credit is called Customer Credit throughout primary UI.
- Cash shift terminology is consistent across navigation, dialogs, status pills, and reports.
- Roles are displayed as Cashier, Pharmacist, and Administrator.

### 5. Error prevention

- Cash received is disabled when the selected payment method is not Cash.
- Customer Credit requires a registered customer before checkout.
- Completing a sale requires an open cash shift.
- High discounts still require manager approval.
- Expired stock remains unsellable and earliest valid expiry allocation remains enforced in the service layer.

### 6. Clear system status

- The shell reports `Ready`, `Needs Attention`, `Shift Open`, or `Shift Closed` instead of technical health wording.
- Sale completion and save failures use short, actionable messages.
- The active signed-in role uses friendly role names.

### 7. Progressive disclosure

System diagnostics are still available to administrators/support staff, but they are hidden behind `Show Technical Details`. Routine users see System Health and Backups first.

### 8. Flexible use for beginners and experts

- Beginners can use labeled buttons and descriptive empty states.
- Experienced operators retain F-key and Alt-number shortcuts.
- The POS remains keyboard-first without forcing shortcuts on new staff.

## SDE principles applied

### Presentation/domain separation

Visible wording is centralized in `ui/ux_copy.py`. User-facing labels are not used as database or business-rule identifiers.

Examples:

- Visible `Customer Credit` → backend value `Khatoo Credit`
- Visible `Cashier` → backend role `Salesman`
- Visible `Administrator` → backend role `Admin`
- Visible `Cash In` → backend movement code `CASH_IN`

This avoids a common large-system failure mode where changing copy breaks queries, permissions, reporting, or migrations.

### Single source of truth for terminology

Navigation, payment names, movement labels, and role labels are defined centrally. New modules should import these definitions instead of duplicating strings.

### Backward compatibility

Existing database values and service contracts remain unchanged. v2.3 changes presentation without requiring a schema migration or invalidating historical data.

### Testable UX contracts

`tests/test_hci_copy_and_domain_separation.py` protects the product language and checks that friendly labels remain decoupled from backend values. Existing MVC and responsive-design tests continue to guard architecture and layout behavior.

## Screen-by-screen result

### New Sale

The POS now starts with the business task, not the subsystem name. The top actions use short verbs, the customer field is marked optional, `Pay with` is simpler than Payment Method, and the checkout action is `Complete Sale`. The held-sale flow says Hold Sale / Resume Sale. Non-cash tender disables Cash received to prevent an irrelevant input.

### Customers

The screen focuses on finding/adding customers and seeing the amount due. `Credit Summary` replaces debt-oriented technical wording, and the aging explanation is written as `How long the balance has been due`.

### Customer Credit

The primary user-facing name is Customer Credit. The screen explains that it is for balances and payments; references, paid, and due amounts use short table labels. Internal Khatoo naming is preserved only where required by legacy data/services.

### Stock & Products

Product setup, stock intake, and alerts are grouped with staff-friendly names. `Add Stock` replaces batch-centric wording. The visible rule is `earliest expiry first`; FEFO remains a technical implementation term.

### Shift & Cash

Opening and closing the counter uses `Start Cash Shift`, `Add / Remove Cash`, and `Count Cash & Close Shift`. The interface describes expected and counted drawer cash directly.

### Reports

KPI labels are reduced to Sales Total, Number of Sales, Cash, and Customer Credit. Tabs are Low Stock, Expiring Soon, and Activity Log.

### Settings

Settings are grouped as General, Staff & Access, and System & Backup. The health card uses plain operational states, while verbose runtime diagnostics are hidden behind Technical Details.

## Large-system product guidance

For future growth, keep these rules:

1. Never bind business rules to visible labels. Store stable IDs/codes and localize the label layer.
2. Keep one terminology catalog for navigation, roles, payments, statuses, and recurring actions.
3. Add contextual help only where the task is ambiguous; do not fill every screen with explanatory text.
4. Use progressive disclosure for administrator/support features.
5. Prefer model-backed tables with paging/filtering for very large datasets.
6. Preserve keyboard accelerators while keeping every critical action discoverable by mouse.
7. Add localization through the copy layer rather than modifying database values; Urdu/Sindhi support can be introduced later without changing domain contracts.
8. Test copy and workflow changes alongside code changes; usability terminology is part of the product contract.

## Acceptance checklist

A first-time cashier should be able to answer these without training documentation:

- Where do I start a sale? → New Sale
- How do I find a customer? → Customers
- Where can I see money a customer owes? → Customer Credit
- Where do I add received stock? → Stock & Products → Add Stock
- How do I start/end the counter day? → Shift & Cash
- Where are sales/stock summaries? → Reports
- Where do I add staff or make a backup? → Settings

If any future screen makes those answers less obvious, its information architecture should be reviewed before release.
