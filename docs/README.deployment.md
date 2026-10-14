# Pharma-Khaato POS — Enterprise Deployment & Build Documentation

This guide provides step-by-step instructions for building, packaging, verifying, and deploying the **Pharma-Khaato Point-of-Sale (POS) & Pharmacy Management System** executable bundle on Linux desktop environments.

---

## 1. Environment & Prerequisites

Ensure the deployment machine or build agent has Python 3.10+ and the required core dependencies installed:

```bash
# Clone repository
git clone <repository-url>
cd project

# Install core runtime & build dependencies
pip install PySide6 pytest pyinstaller
```

---

## 2. Automated Test Suite Verification (Headless Mode)

Before compiling the production bundle, run the full 66-case automated test suite in headless offscreen mode to ensure zero regressions:

```bash
# Execute full suite in offscreen window mode
QT_QPA_PLATFORM=offscreen pytest scripts/
```

Expected output:
```text
============================== 66 passed in 3.84s ==============================
```

---

## 3. Building the Production Executable Bundle

Pharma-Khaato uses PyInstaller with a custom single-folder specification file (`pharma_khaato.spec`).

To build the standalone bundle:

```bash
# Run PyInstaller build
pyinstaller --noconfirm pharma_khaato.spec
```

The output bundle will be generated in `dist/pharma_khaato/`:
- Executable binary: `dist/pharma_khaato/pharma_khaato`
- Internal assets & data directory: `dist/pharma_khaato/_internal/`
- Embedded database location: `dist/pharma_khaato/_internal/data/pharmacy_db.sqlite`

---

## 4. Verification & Testing the Executable

Verify that the compiled binary launches and initializes the SQLite schema cleanly:

```bash
# Test run binary in offscreen mode
QT_QPA_PLATFORM=offscreen timeout 2s ./dist/pharma_khaato/pharma_khaato
```

You should see log output confirming schema creation and automated migrations applied:
```text
[INFO] Creating fresh SQLite embedded database at: .../dist/pharma_khaato/_internal/data/pharmacy_db.sqlite
[INFO] SQLite schema initialized successfully.
[INFO] Successfully applied migration: 001_initial_schema.sql
...
[INFO] Successfully applied migration: 006_cash_movements.sql
```

---

## 5. Database Storage & Backup Operations

### Embedded Database Path
- **Default path:** `dist/pharma_khaato/_internal/data/pharmacy_db.sqlite`
- The database operates in **SQLite WAL (Write-Ahead Logging)** mode for high concurrency and fast transactions.

### Creating On-Demand Database Snapshots
Backups can be triggered directly from the application's **Settings -> Technical Diagnostics** tab or created via CLI:

```bash
# Copy SQLite snapshot while system is running (WAL-safe)
cp dist/pharma_khaato/_internal/data/pharmacy_db.sqlite backups/pharmacy_db_$(date +%Y%m%d_%H%M%S).sqlite
```

---

## 6. Distribution Checklist

1. [x] Test suite passes 100% (`QT_QPA_PLATFORM=offscreen pytest scripts/`)
2. [x] Zero Tkinter or dead GUI dependencies in PyInstaller build spec
3. [x] Keyboard navigation verified for fast billing (Up/Down, Enter, Delete, F10 checkout)
4. [x] Theme and font scaling settings persist to `Pharmacy_Settings` table
5. [x] Bundled binary verified in `dist/pharma_khaato/`
