# PHARMA-KHAATO — COMPREHENSIVE REPOSITORY AUDIT REPORT

**Date:** 2026-08-21  
**Role:** Lead Product Engineer & Architect  
**Scope:** Complete Codebase, Security, Database, POS Workflows, UI Architecture & Packaging  

---

## 1. Actual File Structure
The project is structured into a modular Python application:
```text
project/
├── core/
│   ├── audit_service.py       # Enterprise audit logging service
│   ├── auth_service.py        # PBKDF2 authentication & brute-force protection
│   ├── backup_service.py      # SQLite database snapshot & restore service
│   ├── customer_service.py    # Customer & Khatoo (credit) ledger service
│   ├── db_engine.py           # Database connection factory & translation layer
│   ├── hold_sale_service.py   # Hold/Recall suspended sales engine
│   ├── inventory_service.py   # Product, batch & FEFO allocation service
│   ├── logger.py              # Rotating file logger
│   ├── pos_service.py         # Checkout transaction service
│   └── receipt_service.py     # Thermal invoice generator
├── ui/
│   ├── screens/
│   │   ├── alerts_screen.py   # Health alerts & stock notifications
│   │   ├── billing_screen.py  # Counter POS checkout & cart interface
│   │   ├── home_screen.py     # Operational dashboard
│   │   ├── inventory_screen.py# Product catalog & batch entry
│   │   ├── khatoo_screen.py   # Customer credit ledger & debt settlement
│   │   ├── login_screen.py    # Restricted access login window
│   │   └── reports_screen.py  # Sales history & audit trail tabbed notebook
│   ├── widgets/
│   │   ├── cart_table.py      # Interactive cart Treeview
│   │   └── product_search_bar.py # Debounced search bar
│   ├── app.py                 # Main Tkinter application container & sidebar navigation
│   └── styles.py              # Global typography and color tokens
├── scripts/
│   ├── benchmark.py           # Performance latency & throughput test suite
│   ├── test_flow.py           # End-to-end integration test suite
│   └── test_security.py       # PBKDF2 & security test suite
├── migrations/
│   ├── 001_initial_schema.sql # Initial MySQL schema
│   ├── 002_performance_indexes.sql # Database index optimization
│   └── 003_industry_level_features.sql # Audit log & hold sale tables
├── config.py                  # Environment & business constants
├── main.py                    # Entry point & virtualenv auto-launcher
├── salesman_app.py            # Backward-compatibility legacy wrapper
├── schema_sqlite.sql          # Canonical embedded SQLite schema & seed data
├── pharma_khaato.spec         # PyInstaller build specification
├── requirements.txt           # Python dependencies
├── .env                       # Local environment file
└── .env.example               # Example environment template
```

---

## 2. Actual Dependencies
Defined in `requirements.txt`:
- `mysql-connector-python>=8.0.0` (Optional MySQL connector)
- `python-dotenv>=1.0.0` (Environment variable configuration)
- Standard library dependencies: `sqlite3`, `tkinter`, `hashlib`, `binascii`, `logging`, `datetime`, `json`.

---

## 3. Actual Configuration Behavior
- Configuration parameters are currently read in `config.py` using `os.getenv()`.
- `.env` files are loaded ad-hoc or rely on system environment variables.
- Missing centralized call to `load_dotenv()` in a unified initialization layer.

---

## 4. Security Findings
1. **Production Default Credentials:**
   - Default fallback password `"pharma123"` present in `config.py`.
   - Seeded plain-text hashes for `admin` (`admin123`), `pharmacist` (`pharm123`), `salesman` (`sales123`) in `schema_sqlite.sql`.
   - Hardcoded default input values (`admin` / `admin123`) pre-filled in `ui/screens/login_screen.py`.
   - Live `.env` containing `DB_PASSWORD=pharma123` tracked in project directory.
2. **Missing First-Run Setup:**
   - System assumes database comes pre-seeded with admin account rather than enforcing an administrator creation wizard on first run.

---

## 5. Database Findings
1. **Unsafe MySQL Fallback Violation:**
   - In `core/db_engine.py`, when `USE_MYSQL=true` and MySQL connection fails, the engine logs an error and **silently falls back to embedded SQLite**.
   - *Violation:* Per product specs, a configured MySQL deployment must fail safely and prevent transactional POS operations rather than silently operating against another engine.
2. **Production Database Location:**
   - SQLite database path is currently relative to `BASE_DIR` (`project/pharmacy_db.sqlite`).
   - Executable directory is treated as mutable, violating OS application-data standards.

---

## 6. Product / Data-Model Gaps
1. **Hardcoded Regulatory Data:**
   - Receipt header in `core/receipt_service.py` contains hardcoded fake numbers (`KPK-DRUG-LIC-88492` and NTN `9482019-3`).
2. **Product Schema Completeness:**
   - Products table lacks explicit fields for `barcode`, `alternate_barcode`, `SKU`, `dosage_form`, `strength`, `pack_size`, `rack_location`.
3. **Cash Register / Counter Shift Session:**
   - Lacks `Cash_Register_Session` table for opening cash, cash in/out, closing cash, and variance tracking.

---

## 7. POS Workflow Gaps
1. **Double-Checkout Vulnerability:**
   - Rapid double-pressing of Checkout button / F12 key can submit duplicate checkout requests if network/DB latency occurs.
2. **Money Precision Model:**
   - Financial totals use standard Python `float` instead of `Decimal`, introducing potential floating-point rounding errors on complex cart taxes/discounts.
3. **Barcode Scanner Direct Routing:**
   - Scanner input requires clear barcode focus and auto-add termination without requiring mouse clicks.

---

## 8. GUI Architecture Findings
1. **Tkinter Component Hierarchy:**
   - Clean frame swapping in `ui/app.py`.
   - Modals use standard `messagebox` dialogs which can interrupt high-speed cashier workflows.
2. **Thread Safety:**
   - All UI operations execute on the main GUI thread. Long-running queries could cause minor visual stutter if un-indexed.

---

## 9. GUI Visual Findings
1. **Design System Standardization:**
   - Basic color constants defined in `ui/styles.py`, but individual screens still feature inline hexadecimal color codes (`#f8f9fa`, `#1e293b`, `#16a34a`).
2. **Information Density:**
   - UI controls lack explicit Counter Density Mode vs Management Density Mode styling.

---

## 10. Packaging Findings
1. **PyInstaller Spec (`pharma_khaato.spec`):**
   - Configured for directory bundling (`COLLECT`).
   - Assumes database file exists in local application directory. Needs integration with `PathManager` for user AppData path resolution.

---

## 11. Missing Tests
- Test for explicit MySQL failure non-fallback behavior.
- Test for double-checkout rapid submission locking.
- Test for `Decimal` monetary rounding accuracy.
- Test for First-Run wizard initialization.

---

## 12. Missing Business Decisions
- **Return / Refund Stock Rules:** Policy for whether returned items re-enter sellable batch stock or move to quarantined/damaged inventory (`BUSINESS DECISION REQUIRED`).
- **Discount Authorization Limits:** Configurable max discount percentage before supervisor override is required (`BUSINESS DECISION REQUIRED`).

---

## 13. Proposed Implementation Sequence
- **Phase 0 (Current):** Security & Configuration Foundation, Credentials Cleanup, Centralized `.env`, `PathManager`, & MySQL Fail-Safe Enforcement.
- **Phase 1:** Data Models & Core Services Upgrade (Product schema extensions, `Decimal` money model, PharmacySettings service).
- **Phase 2:** POS Engine, Barcode Scanner Integration, & Double-Checkout Lockout.
- **Phase 3:** Cash Register Shift Sessions & Counter Cash Audit.
- **Phase 4:** Purchasing, Receiving, Supplier Management, & Return/Refund Workflows.
- **Phase 5:** Design System Standardization, Platform Materials & Responsive Desktop UX.
- **Phase 6:** Printing Architecture, Backup/Restore Verification & System Health.
- **Phase 7:** Packaging, Clean Windows Release & Production Acceptance Gate.

---

## 14. Exact Files Modified in Phase 0
1. `config.py` — Centralize `.env` loading, remove default fallback password, instantiate `ApplicationSettings` & `PharmacySettings`.
2. `core/path_manager.py` — Create central OS-compliant path resolution for database, logs, backups, and receipts.
3. `core/db_engine.py` — Remove silent SQLite fallback when `USE_MYSQL=true` and update DB path resolution via `PathManager`.
4. `core/receipt_service.py` — Replace hardcoded license/NTN strings with dynamic settings from `PharmacySettings`.
5. `ui/screens/login_screen.py` — Clear hardcoded pre-filled credentials (`admin` / `admin123`).
6. `schema_sqlite.sql` — Remove seeded default employee passwords; add First-Run Admin check support.
7. `.env` — Sanitize local file (remove plain-text credentials).
8. `.env.example` — Maintain clean template with placeholders.
9. `README.md` & `DEPLOYMENT.md` — Remove plain-text password references.
