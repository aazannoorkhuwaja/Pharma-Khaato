# Pharma-Khaato — Desktop Pharmacy Management

Pharma-Khaato is an offline-first PySide6 desktop pharmacy system for fast counter sales, batch-aware stock, customers, customer credit, cash shifts, returns, reports, receipt printing, staff access, and backups.

> **Database:** local SQLite in WAL mode. Keep the live database on the pharmacy computer; do not place the active SQLite database on a shared/network drive.

## Product status

The current production-candidate work lives on **`develop-ui`** while `main` remains protected from unreviewed migration work.

The branch includes launch/readiness automation for:

- fresh database creation and versioned migrations
- deterministic isolated demo data
- compile + UI source audit + regression tests
- end-to-end business-flow smoke checks
- offscreen GUI navigation smoke checks
- automatic daily integrity-checked backups
- packaged executable smoke testing and release checksums

## Key features

- **New Sale:** fast product/barcode search, cart editing, discounts, hold/resume, multiple payment methods, keyboard shortcuts, shift enforcement, and checkout retry protection.
- **Stock & Products:** products, suppliers, stock intake, low-stock alerts, expiry alerts, bounded catalog loading, and earliest-expiry-first allocation.
- **Customers & Customer Credit:** customer lookup, balances, credit sales, payment history, and partial/full collections.
- **Shift & Cash:** opening cash, drawer movements, cash-only reconciliation, credit collections, and closing balance checks.
- **Returns & Refunds:** sale lookup, controlled quantities, stock restoration, credit adjustment, and audit history.
- **Reports:** sales totals, payment mix, low stock, expiring stock, credit collections, returns, and activity history.
- **Receipts:** five selectable thermal receipt formats including Professional 80mm and Compact 58mm.
- **Staff & Access:** separate Cashier, Pharmacist, Manager/Administrator permissions with password reset and auditability.
- **Data safety:** SQLite WAL, transactional checkout, durable checkout tokens, verified backups, pre-migration backups, and system health checks.
- **Security:** PBKDF2-HMAC-SHA256 password hashing, persistent login lockout, backend permission checks, and audit logging.
- **Responsive UI:** adaptive sidebar modes, DPI-aware sizing, scalable tables, lazy screens, bounded queries, and background workers for slow I/O.

## Quick start

```bash
git clone -b develop-ui https://github.com/aazannoorkhuwaja/Pharma-Khaato.git
cd Pharma-Khaato
python3 scripts/dev_run.py
```

`dev_run.py` creates/reuses `.venv`, installs the correct dependency set only when needed, and launches without modifying system Python.

Normal update/run loop:

```bash
cd Pharma-Khaato
git switch develop-ui
git pull --ff-only
python3 scripts/dev_run.py
```

Do not use `--break-system-packages`.

## One-command demo

The demo is completely isolated under `.demo-data` and does **not** modify the normal pharmacy database.

First verify the complete demo dataset:

```bash
python3 scripts/dev_run.py --demo-check
```

Then launch a freshly reset demonstration:

```bash
python3 scripts/dev_run.py --demo
```

Demo accounts:

```text
Administrator: admin / demo1234
Cashier:       cashier / demo1234
```

Recommended presentation path:

```text
New Sale → Customers → Customer Credit → Stock & Products →
Shift & Cash → Reports → Returns → Settings → Receipts
```

For a rehearsal without resetting existing demo data:

```bash
python3 scripts/dev_run.py --demo-keep
```

See [Demo Guide](docs/DEMO_GUIDE.md) for the full presentation flow.

## Architecture

The application uses an explicit Model-View-Controller boundary:

- `ui/` — PySide6 views, reusable widgets, theme, accessibility, and user-facing copy
- `controllers/` — workflow orchestration and view/backend boundary
- `models/` — Qt-free backend facades
- `core/` — transactions, SQLite, security, reports, receipts, backups, and business rules
- `migrations/` — ordered schema upgrades
- `tests/` — backend, architecture, UI, launch-readiness, and regression coverage

## Project structure

```text
Pharma-Khaato/
├── main.py
├── controllers/
├── models/
├── core/
├── ui/
│   ├── app/
│   ├── screens/
│   ├── theme/
│   └── widgets/
├── migrations/
├── tests/
├── scripts/
├── packaging/
├── docs/
├── requirements.txt
├── requirements-dev.txt
└── pharma_khaato.spec
```

## Quality gates

Install development dependencies once if you are not using the launcher:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Local checks:

```bash
python -m compileall -q main.py controllers core models ui scripts
python scripts/ui_audit.py
QT_QPA_PLATFORM=offscreen python -m pytest -q
python3 scripts/dev_run.py --demo-check
```

Normal pushes to `develop-ui` use the fast Linux/Python 3.14 quality gate. Pull requests and protected/release paths run the wider Windows/Linux Python compatibility matrix plus launch-readiness smoke checks.

## Release build

```bash
python scripts/build_release.py
```

Build native Windows artifacts on Windows and Linux artifacts on Linux, or use the included release workflow. Release automation smoke-tests the packaged executable and produces checksums for distributed artifacts.

Before deploying to a real pharmacy, also complete the hardware acceptance checklist for the exact thermal printer, barcode scanner, cash drawer workflow, and target workstation.

## Documentation

- [Demo guide](docs/DEMO_GUIDE.md)
- [Deployment & packaging](docs/DEPLOYMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database & migrations](docs/DATABASE.md)
- [Developer workflow](docs/DEVELOPER_WORKFLOW.md)
- [Counter user guide](docs/USER_GUIDE.md)
- [Testing](docs/TESTING.md)
- [UI/UX product review](docs/UI_UX_PRODUCT_REVIEW.md)
- [HCI/SDE usability review](docs/HCI_SDE_USABILITY_REVIEW.md)

## Licence

See [LICENSE](LICENSE).
