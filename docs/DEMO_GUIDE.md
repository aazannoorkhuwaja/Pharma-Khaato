# Pharma-Khaato Complete Demo Guide

This guide is designed for a live presentation where the application must start from a predictable state every time. The demo uses `.demo-data/`, which is separate from normal Pharma-Khaato data.

## One-command clean demo

From the repository root:

```bash
python3 scripts/dev_run.py --demo
```

This command:

1. creates/reuses `.venv`,
2. resets only `.demo-data`,
3. builds a realistic pharmacy dataset through the real business services,
4. runs the launch-readiness checks,
5. prints the demo credentials and seeded sale numbers,
6. launches the real application against the isolated demo database.

Demo credentials:

- Administrator: `admin` / `demo1234`
- Cashier: `cashier` / `demo1234`

To rehearse without resetting changes you made during the previous demo:

```bash
python3 scripts/dev_run.py --demo-keep
```

To prepare/verify the demo without opening the GUI:

```bash
python3 scripts/dev_run.py --demo-check
```

## Recommended 8–10 minute presentation

### 1. Login and counter workflow

Sign in as `admin` and start on **New Sale**. Point out barcode/name/formula search, keyboard-friendly workflow, live stock availability, multiple tenders, Customer Credit, hold/resume, and the visible shift state.

Create one small cash sale using `Panadol 500mg`. The seeded shift is already open, so checkout is ready immediately.

### 2. Customers

Open **Customers** and show the preloaded customer directory. Search by name or CNIC and open a customer credit summary. Explain that routine screens hide internal database IDs.

### 3. Customer Credit

Open **Customer Credit**. A seeded credit sale and partial cash repayment are already present. Show the remaining balance, then record another partial payment if desired. Cash credit collections are tied to the open drawer; digital collections do not alter physical cash.

### 4. Stock & Products

Open **Stock & Products** and demonstrate:

- product search,
- supplier-backed stock intake,
- configured reorder levels,
- low stock (`ORS Sachet` is intentionally below its threshold),
- near expiry (`Vitamin C 500mg` is intentionally near expiry),
- FEFO stock allocation.

### 5. Shift & Cash

Open **Shift & Cash**. The demo begins with Rs. 5,000 opening cash and already contains Cash, Card, Easypaisa, JazzCash and Customer Credit activity. Explain that only physical cash tender/collections affect the drawer expectation.

### 6. Reports

Open **Reports** and show today's sales/payment mix, low stock, expiry alerts and activity history. Export is available without blocking the interface.

### 7. Returns & Refunds

When `--demo` starts, the terminal prints several return-ready Sale numbers. Enter one of those Sale numbers in **Returns & Refunds**, select a quantity and reason, then process the return. The system uses original sale/tender records rather than trusting a user-entered refund price.

For the cleanest demonstration, use the seeded **Cash** sale so the refund can be clearly connected to the open shift.

### 8. Receipts and administration

Open **Settings → Receipts** and preview:

- Professional 80mm
- Standard 80mm
- Detailed 80mm
- Tax Invoice 80mm
- Compact 58mm

The demo defaults to **Professional 80mm**. If no physical printer is connected, use Preview; printer availability is not required for the rest of the demo.

Then show **Staff & Access** and **System & Backup**. Diagnostics/backups load outside the GUI thread so opening Settings should remain responsive.

## Before presenting

Run these commands from a clean pull:

```bash
git switch develop-ui
git pull
python3 scripts/dev_run.py --demo-check
```

A successful preflight should finish without an exception. Then launch the clean demo:

```bash
python3 scripts/dev_run.py --demo
```

For an additional business-flow check:

```bash
source .venv/bin/activate
python scripts/test_flow.py
```

For the normal installation/database rather than demo data:

```bash
python3 scripts/dev_run.py --self-check --headless
```

## Recovery during a live demo

If you change data incorrectly or want to restart the presentation, close the app and run:

```bash
python3 scripts/dev_run.py --demo
```

The demo resets only `.demo-data`; it does not delete the real application database.

If a printer is unavailable, use receipt Preview and continue. If a report export destination is inconvenient, skip the export and demonstrate the on-screen report. Neither should block the core sales/inventory/credit/cash demonstration.

## Launch rule

Do not demonstrate from an arbitrary old local database. Use `--demo` for presentations and use normal application data only for actual deployment. A release artifact should be distributed only after its release workflow has passed tests, source self-check, full demo preflight, native packaging, packaged-executable self-check and checksum generation.
