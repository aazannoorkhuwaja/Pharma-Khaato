# Pharma-Khaato v2.2 — UI/UX, Responsive Design & Product Review

> **v2.3 HCI/SDE language pass:** See `HCI_SDE_USABILITY_REVIEW.md` for the task-first terminology, progressive disclosure, error-prevention, and presentation/domain separation work added after this responsive-design review.

## Executive summary

The backend and transaction architecture were already the strongest part of the product. The main frontend weakness was not the visual palette; it was **layout rigidity**. The interface mixed a centralized theme with many screen-level pixel values. As a result, changing the font scale could enlarge some text while leaving dialog dimensions, side panels, buttons, tables, and navigation unchanged. On 1024px laptops or Windows 125–150% DPI scaling, the POS workspace could become cramped even though the same screen looked acceptable at 1366×768.

v2.2 turns the GUI into an **adaptive desktop interface**. The application still behaves like business software rather than a mobile page, but it now responds to available logical pixels, interface scale, and content density.

## Major issues found and resolution

| Area | Previous risk | v2.2 resolution |
|---|---|---|
| Typography | Many `11px`, `12px`, `14px`, `20px` overrides bypassed the global scale | Screen-level literal font sizes removed; semantic `h1`, `h2`, `subtitle`, `caption`, `metric`, `metricLarge` roles are controlled by ThemeManager |
| Buttons | Fixed heights and local padding made 125–150% scaling inconsistent | Global control/action heights scale with the selected interface scale; compact table actions use a dedicated property |
| Main shell | 230px sidebar consumed the same space at every window width | Three shell densities: full, compact, mini |
| POS | 360px checkout panel + full sidebar squeezed the cart | Flexible 292–420px summary panel, proportional 70/30 layout, adaptive sidebar, compact hotkey badges |
| Customer screen | 340px fixed debt panel | Flexible 280–410px panel with scalable metric typography |
| Inventory | 380px fixed intake form and fixed alert table height | Flexible intake panel and bounded, resizable alert table |
| Settings | 340px fixed staff form | Flexible 300–410px staff panel; table keeps priority |
| Dialogs | Hard-coded modal dimensions could fall below taskbar or clip scaled controls | Dialog sizing clamps to current monitor available geometry and supports resizing |
| First-run wizard | Long form could overflow vertically at large scale | Form sections scroll while the primary action remains visible |
| Tables | Dense rows, inconsistent action-button sizing, long text collisions | Scaled row heights, text elision, horizontal/vertical scrollbars, minimum column widths |
| Headers | Titles, status pills and actions competed for horizontal space | Shared ScreenHeader stacks its actions below the title when narrow |
| Reports | Four KPI cards always forced into one row | 4-column wide layout, 2-column compact layout |
| Theme ownership | Reusable cards/buttons duplicated local colors and sizes | Card/button primitives now defer to the global theme so theme/scale changes propagate consistently |

## Responsive behavior

### Main application shell

The shell uses logical Qt pixels, which means Windows display scaling is taken into account by Qt.

- **Full mode — width ≥ 1260:** 230px sidebar, navigation names + shortcuts, full clock and shortcut hint bar.
- **Compact mode — width 1080–1259:** 176px sidebar, navigation names without duplicated shortcut text, shorter clock.
- **Mini mode — width < 1080:** 84px sidebar, abbreviated navigation labels, compact clock, nonessential sidebar metadata hidden.
- Minimum supported main-window size is **900×600 logical pixels**.

This matters most for POS. At 1024px the old shell could leave roughly 794px for content before margins; the mini shell returns roughly 940px to the work area.

## Typography and control scale

Base semantic scale at 1.0x:

- H1: 22px
- H2: 16px
- Body: 13px
- Secondary/caption: 11px
- Standard control target: 38px logical height
- Primary action target: 44px logical height
- Standard table row: 38px logical height

The Settings screen exposes 1.0x, 1.25x, and 1.5x **Interface Scale (Text + Controls)**. The important change is that this is no longer merely a font multiplier; form controls, buttons, tab targets, scrollbars, table padding, choice indicators, and key semantic metrics scale with it.

## Screen-by-screen UX assessment

### POS Counter

This is the highest-priority screen and receives the most conservative layout treatment.

**Strengths retained**
- Keyboard-first product search.
- Fast cart editing and checkout.
- Customer lookup and credit selection are visible in the same workflow.
- Total remains the strongest visual metric.

**v2.2 improvements**
- Search input receives a dedicated scalable primary-search treatment.
- Checkout summary is flexible rather than fixed at 360px.
- Hotkey badges collapse from `[F1] Search` to `[F1]` when space is constrained.
- Customer result table can grow within bounds instead of being locked to 110px.
- Empty-cart and total states use semantic global styles.
- The checkout action keeps a larger minimum target than ordinary controls.

### Customer Directory

The table remains the primary information surface. Debt information is secondary and therefore keeps a bounded side panel rather than competing for half the screen. The debt amount uses scalable metric typography and explanatory text wraps.

### Khatoo Ledger

The ledger is table-first, with compact in-row payment actions. Payment dialogs are monitor-aware and resizable. Compact action buttons do not inherit the oversized primary-action target intended for checkout/save actions.

### Inventory

The screen keeps three task modes—catalog, intake, alerts—but tab controls now inherit scalable global styling and scroll when labels do not fit. Stock intake uses a bounded flexible form panel instead of a fixed 380px card.

### Cash Register

Status is visible at the header level, while register operations remain explicit and separate. Open, movement, and close actions have semantic success/primary/danger roles. The active-session explanation wraps instead of forcing the panel wider.

### Reports

Executive KPI cards automatically change from four columns to two under the compact breakpoint. This avoids tiny cards and unreadable currency metrics. Data tables remain horizontally scrollable for wide operational datasets.

### Settings & Administration

The settings UI now describes 1.0x/1.25x/1.5x as **interface scaling**, matching actual behavior. Staff creation is a flexible side panel and the staff table receives the majority of available width. Tabs use scroll buttons for smaller workspaces.

### Login and First Run

Startup dialogs are sized against the current monitor. The first-run form becomes vertically scrollable at large accessibility scales while keeping the completion button visible, which is important on 1366×768 hardware.

## Accessibility and usability rules

The current product standard is:

1. Do not introduce literal screen-level `font-size: Npx` rules.
2. Do not use `setFixedWidth()` or `setFixedSize()` for business content panels.
3. Use semantic object names/properties for typography and action hierarchy.
4. Keep important actions at least the global control target; primary actions are larger.
5. Tables may scroll horizontally. They must not crush columns until text becomes ambiguous.
6. Secondary explanatory labels wrap; financial values use metric roles.
7. Keyboard shortcuts remain functional even when visual shortcut labels collapse.
8. Dialogs must be resizable or bounded to available monitor geometry.
9. New large screens should use shared `Card`, `ScreenHeader`, `BadgePill`, `polish_table`, and responsive helpers instead of local style systems.

`python scripts/ui_audit.py` enforces the most important static rules without requiring PySide6.

## Large-system suitability

The GUI is now structured more like an enterprise desktop product:

- **Design system ownership:** palette, typography, control heights and responsive metrics have clear central owners.
- **Composable primitives:** reusable cards, headers, badges, tables and semantic buttons reduce screen drift.
- **Regression guardrails:** source-level responsive tests prevent fixed widths and literal screen font sizes from returning silently.
- **Workstation range:** compact laptop/counter displays and large desktop monitors use the same code path with adaptive density.
- **Data growth:** operational tables scroll and elide safely instead of relying on a small fixed dataset.
- **Role growth:** the MVC/router/RBAC structure already supports additional modules without coupling them to POS.
- **Operational safety:** UI changes do not alter the transaction, audit, inventory allocation, cash-session, credit, backup, or authentication services.

## Large-deployment boundary and next architecture step

v2.2 is **large-screen / large-workflow ready**, but it is important not to confuse that with a multi-branch enterprise backend. The current product is intentionally offline-first and SQLite-based. That is excellent for a pharmacy counter or a controlled local deployment, but a truly large organization with many simultaneous terminals, branches, central inventory, and tens of thousands of rows per operational view should add a server API and centralized database rather than placing the SQLite file on a network share.

The frontend has been prepared for that evolution: MVC controllers isolate the Views from backend services, search results already use a model-backed `QTableView`, and layout/design primitives are centralized. For enterprise data volumes, the remaining table-first screens should progressively move from eager `QTableWidget` population to `QTableView` + `QAbstractTableModel` with server-side pagination/filtering, background loading, cached lookup lists, and explicit loading/empty/error states. This is a scale roadmap rather than a blocker for the current offline-counter product.

For a multi-site edition, the recommended next layer is: centralized API/authentication, PostgreSQL (or equivalent transactional server database), branch/tenant scoping, permission policies beyond screen-level RBAC, asynchronous sync/jobs, observability/health metrics, conflict handling for offline terminals, centralized backup/restore, and deployment telemetry. The current MVC boundary means those services can be introduced without redesigning every screen.

## Remaining native validation requirement

The source environment used for this pass does not include the PySide6 runtime, so a native rendered screenshot/interaction run could not be executed here. Backend and source-level regression tests are green, but final release acceptance should still run the GUI on at least:

- Windows 11 at 100%, 125%, and 150% display scale.
- 1366×768 and 1920×1080 Windows workstations.
- A mainstream Linux desktop under X11 or Wayland at 100% and 125% scale.
- Both Light and Dark themes.
- Interface scales 1.0x, 1.25x and 1.5x.

The included universal test launcher is intended to make that native acceptance pass easy.

# Complete product overview

**Pharma-Khaato** is an offline-first pharmacy operations suite centered on fast POS checkout and reliable stock/credit accounting. It is a native PySide6 desktop application using explicit MVC boundaries, with SQLite in WAL mode for local reliability.

### Core modules

- **POS:** search/scan, cart, discount, tax, cash received/change, multiple payment methods, hold/recall and checkout.
- **Customers:** CNIC-based customer records, directory search and debt profile.
- **Khatoo:** credit issuance, outstanding balances, partial/full settlement and ledger inspection.
- **Inventory:** product master, suppliers, batch intake, FEFO-aware stock, near-expiry and reorder alerts.
- **Cash register:** opening float, cash movements, expected cash and end-of-shift reconciliation.
- **Reports:** daily sales KPIs, reorder report, expiry risk and security/audit trail.
- **Administration:** pharmacy rules, tax/receipt configuration, theme/interface scale, staff roles, diagnostics and backups.

### Architecture

`ui/` Views → `controllers/` orchestration → `models/` backend facades → `core/` business/data services → SQLite.

The separation keeps UI work from bypassing business rules and makes large-screen additions or redesigns safer.

### Security and reliability

- Versioned PBKDF2-HMAC-SHA256 password hashes with legacy upgrade support.
- Persistent login lockout controls.
- Role-based screen access.
- Audit logging.
- Atomic checkout/database transactions.
- SQLite WAL mode.
- Snapshot backups.
- Central logging and exception handling.

### Deployment model

The production build remains native per operating system because Qt/PyInstaller binaries are platform-specific. Windows releases must be built on Windows and Linux releases on Linux. For UI evaluation, `PharmaKhaato-v2.3.1-Universal-Test.py` is a single cross-platform bootstrap file that extracts the bundled app, creates an isolated virtual environment, installs its Python-compatible runtime requirements on first launch, and starts the application.
