# Pharma-Khaato — Desktop Pharmacy Management

Pharma-Khaato is an offline-first desktop application for pharmacy sales, customers, customer credit, stock, cash shifts, reports, staff access, and backups. The interface is designed for fast counter work while remaining easy to learn for non-technical staff.

> **Database:** local SQLite in WAL mode. Keep the live database on the pharmacy computer; do not place it on a shared/network drive.

## Architecture

The application uses an explicit **Model-View-Controller (MVC)** boundary:

- `ui/` — PySide6 views, reusable widgets, theme, accessibility and user-facing copy
- `controllers/` — workflow orchestration and UI boundary normalization
- `models/` — Qt-free backend facades
- `core/` — transactional business rules, SQLite access, security, reports and backups
- `migrations/` — versioned schema changes
- `tests/` — backend, architecture, UI-source and regression tests

## Key features

- **New Sale:** barcode/product search, cart editing, discounts, hold/resume, multiple payment methods and keyboard shortcuts.
- **Stock & Products:** products, suppliers, stock intake, low-stock alerts, expiry alerts and earliest-expiry-first allocation.
- **Customers & Customer Credit:** customer lookup, balances, credit sales and partial/full payment recording.
- **Shift & Cash:** opening cash, drawer movements, expected cash and closing reconciliation.
- **Reports:** sales totals, low stock, expiring products and activity history.
- **Staff & Access:** separate Cashier, Pharmacist and Administrator accounts.
- **Data safety:** atomic checkout, SQLite WAL, integrity-checked backups, safety backup before restore and system health checks.
- **Security:** PBKDF2-HMAC-SHA256 password hashing, persistent login lockout and audit logging.
- **Responsive desktop UI:** adaptive navigation, DPI-aware sizing and 1.0x/1.25x/1.5x interface scaling.
- **Cross-platform quality gate:** Windows/Linux CI on Python 3.12 and 3.14.

## Quick start — development branch

The active PySide6 product is currently developed on `develop-ui`.

```bash
git clone -b develop-ui https://github.com/aazannoorkhuwaja/Pharma-Khaato.git
cd Pharma-Khaato
python3 scripts/dev_run.py
```

`dev_run.py` creates/reuses a local `.venv`, installs the correct PySide6 version for the current Python interpreter when needed, and launches the app without modifying system Python.

After the first setup, the normal development/test loop is:

```bash
cd Pharma-Khaato
git pull
python3 scripts/dev_run.py
```

### Manual environment setup

If you prefer to manage the environment yourself:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows PowerShell/cmd equivalent
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

Do not install dependencies into the system Python and do not use `--break-system-packages`.

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

## Testing

Install development dependencies once:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Then run the same core gates used by CI:

```bash
python -m compileall -q main.py controllers core models ui scripts
python scripts/ui_audit.py
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

GitHub CI executes those checks on Windows and Linux with Python 3.12 and 3.14.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database & migrations](docs/DATABASE.md)
- [Deployment & packaging](docs/DEPLOYMENT.md)
- [Developer workflow](docs/DEVELOPER_WORKFLOW.md)
- [Counter user guide](docs/USER_GUIDE.md)
- [UI/UX product review](docs/UI_UX_PRODUCT_REVIEW.md)
- [HCI/SDE usability review](docs/HCI_SDE_USABILITY_REVIEW.md)

## Release build

```bash
python scripts/build_release.py
```

Build Windows artifacts on Windows and Linux artifacts on Linux, or use the included release workflow. Test a release against a fresh data directory before distributing it.
