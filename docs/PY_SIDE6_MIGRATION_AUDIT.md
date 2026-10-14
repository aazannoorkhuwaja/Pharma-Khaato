# PHARMA-KHAATO — PYSIDE6 / QT NATIVE DESKTOP MIGRATION AUDIT

## 1. Executive Summary

This document performs a comprehensive repository audit to guide the migration of **Pharma-Khaato** from a hybrid Web/Tkinter interface into a **100% Native Windows Desktop Application** built with **PySide6 (Qt for Python)**.

---

## 2. Component Categorization & Dependency Analysis

### A. Core Business Backend (`core/`) — KEEP & PRESERVE (100%)
The core layer contains all validated, production-grade business logic, database transaction engine, security mechanisms, and FEFO inventory rules. **None of this will be discarded or rewritten.**

| File | Purpose | PySide6 Integration Strategy | Status |
| :--- | :--- | :--- | :--- |
| `core/auth_service.py` | PBKDF2 hashing, login_user, brute-force lockouts | Called directly by Qt Login Controller/Screen | PRESERVE |
| `core/db_engine.py` | Connection pooling, SQLite WAL, ACID transactions | Shared DB access layer for Qt app | PRESERVE |
| `core/inventory_service.py` | Stock search, FEFO queries, master product & batch creation | Called by POS and Inventory Controllers | PRESERVE |
| `core/pos_service.py` | Transaction engine, atomic sale confirmation, inventory decrement | Called by POS Billing Controller | PRESERVE |
| `core/customer_service.py` | Customer CNIC registration, Khatoo credit management | Called by Customers & Khatoo Controllers | PRESERVE |
| `core/cash_session_service.py`| Cash float, shifts, session close & cash discrepancy | Called by Shift / Cash Session Controller | PRESERVE |
| `core/hold_sale_service.py` | Hold / recall suspended sales queue | Called by POS Hold/Recall dialog | PRESERVE |
| `core/receipt_service.py` | Invoice generation, receipt formatting | Called by Native Thermal/PDF Printer Service | PRESERVE |
| `core/reports_service.py` | Daily sales, inventory reorder, audit logs | Called by Reports Controller | PRESERVE |
| `core/backup_service.py` | Automated database snapshots & restoration | Called by Admin Settings Dialog | PRESERVE |
| `core/audit_service.py` | Event logging & compliance trail | Automatic event log on state changes | PRESERVE |
| `core/migration_manager.py` | DDL schema migration runner | Called during Qt Application Bootstrap | PRESERVE |
| `core/path_manager.py` | OS-specific app data paths (`~/.gemini/antigravity`) | Used by Qt app for config/DB paths | PRESERVE |
| `core/settings_service.py` | Key-value settings storage | Used by Qt Theme & App Preferences | PRESERVE |
| `core/logger.py` | Structured logging | Application-wide logger | PRESERVE |

---

### B. Web-Only Code & Assets — SAFE TO REMOVE (Phase A)
Inspection proves that `web_server.py` is strictly an HTTP standard library wrapper over `core/` functions, and `ui/index.html` is a web SPA mockup. No unique business logic exists exclusively in these web files.

| File / Component | Purpose | Disposal Decision |
| :--- | :--- | :--- |
| `web_server.py` | Multi-threaded HTTP REST API server | **REMOVE** (Unnecessary local HTTP server) |
| `ui/index.html` | Web SPA interface (Tailwind HTML/JS) | **REMOVE** (Replaced by native PySide6 UI) |
| `ui/analytics_dashboard.html` | Web Analytics template | **REMOVE** (Replaced by native PySide6 UI) |
| `main.py` (web launcher parts) | `launch_web`, `webbrowser.open` logic | **REFACTOR** (To launch Qt QApplication directly) |

---

### C. Existing Legacy Tkinter UI (`ui/`) — MIGRATION TARGET
The current repository contains an early Tkinter UI prototype (`ui/app.py`, `ui/screens/*.py`). This layout structure will be converted to high-performance PySide6 Qt Widgets.

| Legacy Tkinter Screen | Target PySide6 / Qt View |
| :--- | :--- |
| `ui/app.py` | `ui/app/main_window.py` & `ui/app/router.py` |
| `ui/screens/login_screen.py` | `ui/screens/login/login_view.py` |
| `ui/screens/billing_screen.py` | `ui/screens/pos/pos_view.py` (Highest Priority) |
| `ui/screens/inventory_screen.py` | `ui/screens/inventory/inventory_view.py` |
| `ui/screens/khatoo_screen.py` | `ui/screens/khatoo/khatoo_view.py` |
| `ui/screens/cash_session_screen.py` | `ui/screens/cash_session/cash_session_view.py` |
| `ui/screens/reports_screen.py` | `ui/screens/reports/reports_view.py` |
| `ui/screens/alerts_screen.py` | Integrated into POS & Status Pills |

---

### D. Packaging & Infrastructure Dependencies

- **`requirements.txt`**: Add `pyside6>=6.5.0` (pinned compatible version).
- **`pharma_khaato.spec`**: Update PyInstaller specification to include PySide6 Qt binaries and remove web dependencies.

---

## 3. Phase Migration Plan

```text
PHASE A — Remove Web Dependency Safely (COMPLETED IN NEXT STEP)
PHASE B — PySide6 Foundation & Architecture Setup
PHASE C — Application Data & Native Lifecycle Setup
PHASE D — First-Run Setup & Configuration Wizard
PHASE E — Design System & Custom Glass-Inspired Qt Theme
PHASE F — Main Window & Compact Navigation Frame
PHASE G — POS Billing Screen & F1-F12 Hotkey Matrix
PHASE H — Modern Qt Widgets (Toast, Dialogs, Status Pills)
PHASE I — Inventory & Supplier Management Screens
PHASE J — Khatoo Debt Settlement Ledger
PHASE K — Cash Register & Shift Dashboard
PHASE L — Printing, Backup & Settings
PHASE M — Accessibility, DPI Scaling & Performance Tuning
PHASE N — PyInstaller Packaging & Native Windows Executable
```

---

## 4. Verification Checklist Before Implementation

- [x] All 8 master cross-verification test suites in `scripts/test_master_cross_verification.py` pass 100%.
- [x] No core business logic is lost by removing `web_server.py`.
- [x] PySide6 dependency identified and targeted for clean installation.
