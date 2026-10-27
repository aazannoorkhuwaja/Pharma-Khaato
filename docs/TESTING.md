# Pharma-Khaato Testing & Verification Manual

Every automated check below uses an isolated disposable shop
(`tests/conftest.py` sets `PHARMA_KHAATO_DATA_DIR`), so none of them touch real
shop records or the owner's application-data folder.

## 1. Source regression suite (the launch gate)

```bash
python -m pytest -q --show-capture=no
```

The suite includes offscreen Qt checks, so the machine needs the Qt runtime
libraries. On a bare Linux container without a desktop stack, install them or
point the loader at them before running:

```bash
QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH=/path/to/lib python -m pytest -q
```

Missing Qt libraries show up as a `libEGL.so.1` / `libxkbcommon.so.0` import
failure at collection time, not as a test failure.

## 2. Isolated business flow

```bash
python scripts/demo_mode.py --no-launch
python scripts/test_flow.py
```

Seven stages over the `.demo-data` shop: sign-in, indexed stock search, cash
shift and drawer totals, customer credit, tender-aware reports, return lookup
and the launch self-check.

## 3. Offscreen screen check

```bash
python scripts/test_gui_auto.py
```

Signs in and opens every main screen offscreen.

## 4. Layout and design-token audit

```bash
python scripts/ui_audit.py
```

Six source-level layout/theme checks.

## 5. Disposable installed-shop functional check

```bash
python main.py --functional-smoke --headless
python main.py --functional-smoke --headless --smoke-report report.json
```

Creates a temporary shop, exercises the real owner-setup and sign-in screens and
shop operations, then deletes it. This is the check the packaged executable must
pass before a release artifact is considered usable.

## 6. Migration and security checks

```bash
python scripts/test_migration.py
python scripts/test_security.py
```

Fresh-database migration, ordered/idempotent upgrade behaviour, PBKDF2
authentication, brute-force lockout, CNIC validation, input bounds and database
backup/restore.

## 7. Launch self-check

```bash
python main.py --self-check --headless
```

Writable storage, SQLite integrity and schema, WAL mode, free space, backup age
and runtime readiness. The same run reconciles the shop's own records: stock
totals against batch quantities, saved sale arithmetic, customer credit
balances against their sales, refunds against sale values, closed shifts
against their sales and cash movements, and rows whose parent record is
missing. Any disagreement is a failure, not a warning, because it means the
file changed outside the application or a restore was incomplete. Exit status
`0` is ready, `2` is not.

## Not covered here

Windows installer/signing, the physical receipt printer, the barcode scanner and
the cash drawer are native or hardware checks. They are tracked in
[docs/WINDOWS_DELIVERY.md](WINDOWS_DELIVERY.md) and the acceptance record in
[docs/REAL_WORLD_READINESS.md](REAL_WORLD_READINESS.md). A green Linux run must
not be reported as native acceptance.
