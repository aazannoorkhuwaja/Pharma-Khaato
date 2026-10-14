# Pharma Khaato

**Pharmacy POS & Inventory Management for independent pharmacies and surgical stores.**

Pharma Khaato is a local-first desktop product built around the work that happens at a pharmacy counter: billing quickly, tracking batch/expiry stock, managing customer credit, balancing cash, handling returns, printing receipts, and protecting business data.

## What it does

- **Fast counter billing** — product/barcode lookup, keyboard-first cart editing, discounts, hold/resume, cash/card/Easypaisa/JazzCash/customer-credit payments, and safe checkout retry handling.
- **Batch-aware inventory** — supplier stock intake, expiry visibility, low-stock warnings and earliest-expiry-first allocation.
- **Customer credit (Khaato)** — customer balances, credit sales, partial/full repayments and payment history.
- **Shift & cash control** — opening cash, cash-in/cash-out, expected drawer balance and closing reconciliation. Digital tenders do not inflate physical cash.
- **Returns & refunds** — controlled return quantities, stock restoration, refund tracking and customer-credit adjustment.
- **Operational reports** — sales, payment mix, low stock, expiring stock, credit collections, returns and activity history.
- **Thermal receipts** — five selectable formats for common 80 mm and 58 mm workflows, with an in-app preview.
- **Staff access** — separate staff accounts and role-based permissions with auditable activity.
- **Recovery & support** — automatic daily backups, manual backup/restore, system checks and a privacy-conscious diagnostics bundle.

## Designed for an offline pharmacy counter

The live business database is SQLite in WAL mode and is stored in the signed-in user's application-data directory. The normal product does not require an internet connection to bill customers.

**Important:** keep the live SQLite database on the pharmacy workstation. Do not place the active database on a network share. Multi-branch/shared-database operation requires a different central-server architecture.

## Customer installation

A released Windows build is intended to be installed through the versioned **Pharma Khaato Setup** executable. The installer creates Start Menu integration, keeps the business database outside the installation directory, and preserves user data across ordinary application upgrades.

Release artifacts are versioned and accompanied by SHA-256 checksums. Windows release automation also smoke-tests the packaged executable before an installer is published.

Before first production use on a new workstation, complete the hardware acceptance checklist for the exact thermal printer, barcode scanner and any cash-drawer workflow.

## First-run experience

On a fresh installation Pharma Khaato creates its local data folders/database, applies schema migrations, then guides the owner through the initial administrator setup. After sign-in, the administrator can configure the pharmacy profile, receipt format, staff accounts, business rules and backups from **Settings**.

The application protects a local data directory from being opened by two interactive Pharma Khaato instances at the same time.

## Demo / evaluation

The repository includes a deterministic demo environment that is isolated from the normal pharmacy database.

```bash
python3 scripts/dev_run.py --demo-check
python3 scripts/dev_run.py --demo
```

Demo accounts:

```text
Administrator: admin / demo1234
Cashier:       cashier / demo1234
```

Suggested evaluation flow:

```text
New Sale → Customers → Customer Credit → Stock & Products →
Shift & Cash → Reports → Returns & Refunds → Settings → Receipts
```

See [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) for the scripted presentation flow.

## Data protection and recovery

Pharma Khaato includes:

- transactional checkout and checkout-request idempotency
- SQLite foreign keys and WAL mode
- ordered database migrations with safety backups for risky upgrades
- automatic daily integrity-checked backups with retention
- manual backup and guarded restore (a safety backup is created before restore)
- login lockout and backend permission enforcement
- rotating application logs
- a support bundle that excludes the live database, receipts, exports and backups by default

Read [`SECURITY.md`](SECURITY.md) and [`SUPPORT.md`](SUPPORT.md) before production deployment.

## Current product status

The active product is being finalized on `develop-ui`. A history-connected `launch-candidate` branch is used for the full review/CI bridge into `main`; `main` is not updated until the launch candidate is explicitly approved.

A launch candidate is considered shippable only when the exact candidate commit passes the regression suite, fresh-install self-check, isolated demo/business-flow smoke, major-screen GUI smoke and supported Windows/Linux compatibility gates. Physical hardware acceptance remains a real-device check.

## For developers

The desktop application uses PySide6 with an explicit MVC boundary:

```text
ui/           views, widgets, theme and operator-facing interaction
controllers/  workflow orchestration / UI-to-domain boundary
models/       Qt-free backend facades
core/         transactions, SQLite, security, reports, receipts and recovery
migrations/   ordered schema upgrades
tests/        regression, architecture, UI and launch-readiness coverage
packaging/    native installer/desktop integration
```

### Development quick start

```bash
git clone -b develop-ui https://github.com/aazannoorkhuwaja/Pharma-Khaato.git
cd Pharma-Khaato
python3 scripts/dev_run.py
```

`dev_run.py` creates/reuses a project `.venv` and installs dependencies only when required. Do not use `--break-system-packages`.

### Local quality gate

```bash
python -m compileall -q main.py controllers core models ui scripts
python scripts/ui_audit.py
QT_QPA_PLATFORM=offscreen python -m pytest -q
python3 scripts/dev_run.py --demo-check
```

Normal `develop-ui` pushes use a fast quality gate. Pull requests and protected/release paths run the wider Windows/Linux compatibility matrix and launch-readiness smoke checks.

### Build a release artifact

```bash
python scripts/build_release.py
```

On Windows, with Inno Setup installed:

```powershell
./packaging/windows/build-installer.ps1
```

The tagged GitHub release workflow builds and smoke-tests platform artifacts automatically.

## Documentation

- [Counter user guide](docs/USER_GUIDE.md)
- [Demo guide](docs/DEMO_GUIDE.md)
- [Deployment & packaging](docs/DEPLOYMENT.md)
- [Database & migrations](docs/DATABASE.md)
- [Testing](docs/TESTING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Developer workflow](docs/DEVELOPER_WORKFLOW.md)
- [Support](SUPPORT.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Licence

See [LICENSE](LICENSE).
