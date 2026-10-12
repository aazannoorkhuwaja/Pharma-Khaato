# Pharma-Khaato — Desktop Pharmacy Management

Pharma-Khaato is an offline-first desktop application for pharmacy sales, customers, customer credit, stock, cash shifts, reports, staff access, and backups. The interface is designed for fast counter work while remaining easy to learn for non-technical staff.

> **Database Engine Notice:** Pharma-Khaato operates exclusively on a local, zero-configuration SQLite database in WAL mode.

---

## Architecture

Pharma-Khaato now uses an explicit **Model-View-Controller (MVC)** boundary: PySide6 screens are Views, `controllers/` coordinates workflows, `models/` provides Qt-free backend facades, and `core/` contains business/data services. Views are guarded by tests from importing backend services directly.

The app is packaged natively for both **Windows and Linux**. See `docs/ARCHITECTURE.md` and `docs/DEPLOYMENT.md`.

---

## Key Features

- **New Sale:** Fast barcode/product search, cart editing, discounts, hold/resume, multiple payment methods, and keyboard shortcuts.
- **Stock & Products:** Products, suppliers, batch intake, low-stock alerts, expiry alerts, and automatic earliest-expiry-first stock allocation.
- **Customers & Customer Credit:** Customer lookup, balances, credit sales, limits, and partial/full payment recording.
- **Shift & Cash:** Opening cash, cash movements, expected drawer balance, and shift closing reconciliation.
- **Reports:** Sales totals, payment mix, low stock, expiring products, and activity history.
- **Staff & Access:** Role-based access for Cashiers, Pharmacists, and Administrators.
- **Responsive Desktop UI:** Adaptive navigation, DPI-aware sizing, flexible work panels, and 1.0x/1.25x/1.5x interface scaling.
- **Security & Reliability:** Versioned PBKDF2-HMAC-SHA256 password hashing, login lockout, audit logs, atomic transactions, SQLite WAL mode, backups, and global crash logging.
- **HCI/SDE Language Layer:** User-friendly labels are separated from stable backend values through `ui/ux_copy.py`, so wording/localization can change without breaking business logic.
- **Cross-platform Delivery:** Native Windows/Linux build workflows plus a single universal test launcher for GUI acceptance testing.

---

## Quick Start

### 1. Installation & Environment Setup

```bash
# Clone repository
git clone https://github.com/aazannoorkhuwaja/Pharma-Khaato.git
cd Pharma-Khaato/project

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Application

```bash
python3 main.py
```

### One-file Windows/Linux UI test

The release bundle includes `PharmaKhaato-v2.3.1-Universal-Test.py`. The **same file** can be launched on Windows or Linux with Python 3.10+:

```bash
# Windows
py PharmaKhaato-v2.3.1-Universal-Test.py

# Linux
python3 PharmaKhaato-v2.3.1-Universal-Test.py
```

On first launch it extracts an isolated test copy, creates a private virtual environment, installs the Python-compatible PySide6 runtime, and opens the desktop application. First launch therefore needs internet access; later runs reuse the cached runtime. Test data is stored separately from a normal Pharma-Khaato installation. A single precompiled native executable cannot be shared between Windows and Linux because Qt/PyInstaller binaries are OS-specific.


---

## Project Structure

```
project/
├── main.py                  # Entry point with environment detector
├── salesman_app.py          # Backward-compatibility UI wrapper
├── controllers/             # MVC workflow/orchestration layer
├── models/                  # Qt-free MVC model facades
├── core/                    # Core Business Services & Data Layer
│   ├── auth_service.py      # Authentication & PBKDF2 security
│   ├── pos_service.py       # Checkout, transaction processing & expiry allocation
│   ├── customer_service.py  # Customer registration & credit ledger
│   ├── inventory_service.py # Products, batches & supplier master data
│   ├── backup_service.py   # Snapshot database backup & restore
│   ├── logger.py           # Centralized rotating file logger
│   └── db_engine.py         # SQLite WAL connection/transaction factory
├── ui/                      # Modular PySide6 Desktop Interface
│   ├── app/                 # Main application shell, router & state manager
│   ├── theme/               # Design tokens, typography & theme manager
│   ├── widgets/             # Reusable UI components & QAbstractTableModel models
│   ├── ux_copy.py            # Central user-facing terminology / domain label mapping
│   └── screens/             # Independent task screens (Sale, Customer, Credit, etc.)
├── migrations/              # Database versioned DDL scripts
├── scripts/                 # Automated test suites & benchmarks
└── pharma_khaato.spec       # PyInstaller packaging configuration
```

---

## Documentation Index

- [Architecture Guide](docs/ARCHITECTURE.md)
- [Database Schema & Migrations](docs/DATABASE.md)
- [Deployment & Packaging Guide](docs/DEPLOYMENT.md)
- [Developer Workflow](docs/DEVELOPER_WORKFLOW.md)
- [Counter User Guide](docs/USER_GUIDE.md)
- [UI/UX & Product Review](docs/UI_UX_PRODUCT_REVIEW.md)
- [HCI/SDE Usability Review](docs/HCI_SDE_USABILITY_REVIEW.md)


## Cross-platform Release Build

```bash
python scripts/build_release.py
```

Build on Windows for the Windows artifact and Linux for the Linux artifact, or use the included cross-platform GitHub Actions release workflow.
