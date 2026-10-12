# Developer Workflow

## One-time local setup

Use the repository-managed launcher for normal development:

```bash
git switch develop-ui
python3 scripts/dev_run.py
```

The launcher creates/reuses `.venv`, installs dependencies when `requirements.txt` changes, and launches the application without writing to system Python.

Daily loop:

```bash
git pull
python3 scripts/dev_run.py
```

## MVC change workflow

### Views / interaction
1. Implement presentation under `ui/screens`, `ui/widgets`, `ui/theme`, or `ui/ux_copy.py`.
2. Do not import `core` business/database services from views.
3. Route user actions through controllers.
4. Keep formatting, widget state, accessible names, focus behavior and keyboard behavior in the UI layer.
5. Keep internal database identifiers out of routine staff-facing screens unless the identifier is itself a real pharmacy concept the user needs.

### Controllers
1. Put cross-feature orchestration in `controllers/`.
2. Normalize UI input at the boundary where useful.
3. Coordinate multiple models for workflows such as POS checkout.
4. Do not execute SQL in controllers.

### Models / core
1. Expose backend behavior through `models/services.py`.
2. Keep models Qt-free.
3. Put transaction, validation and database rules in `core/`.
4. Use `core.db_engine.get_db()` for atomic commit/rollback behavior.
5. Keep user-facing copy out of database values; map stable domain values through the UI copy layer.

## Quality gate

Install development dependencies into `.venv`:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Run before pushing a substantial change:

```bash
python -m compileall -q main.py controllers core models ui scripts
python scripts/ui_audit.py
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

CI repeats those checks on:

- Ubuntu + Python 3.12
- Ubuntu + Python 3.14
- Windows + Python 3.12
- Windows + Python 3.14

Do not merge around a red matrix job simply because another operating system passes; cross-platform failures have already caught real SQLite/Qt lifecycle bugs.

## Product/HCI checklist

Before considering a screen finished, verify:

- the primary task is visually obvious;
- routine tables show business information, not internal IDs;
- primary actions use short verb-first labels;
- keyboard shortcuts remain available without dominating the screen;
- money uses consistent `Rs.` formatting;
- empty/no-result/error states tell the user what to do next;
- destructive actions are explicit and visually distinct;
- focus order, accessible names and keyboard activation work;
- light/dark modes use semantic theme tokens rather than stale hard-coded screen colors;
- high-volume datasets are bounded or model-backed rather than populated indefinitely into eager widgets.

## Data-safety checklist

- Never place the live SQLite database on a network share.
- Preserve WAL mode and transaction boundaries.
- Create/verify a safety backup before destructive restore operations.
- Never commit databases, receipts, logs, `.env`, backups or virtual environments.
- Treat migration, restore and administrative account actions as privileged workflows.
- Keep internal audit identifiers in logs/audit storage, not routine counter UI.

## Security checklist

- Keep credential handling in `core.auth_service`.
- Use the centralized password policy; do not duplicate password-length rules in screens/services.
- Never log passwords or reset values.
- Use parameterized SQL for user/database values.
- Keep login lockout and audit events persistent.
- Sensitive business permissions should be enforced beyond merely hiding a button where practical.

## Performance checklist

- Keep long-running I/O off interactive widget callbacks where practical.
- Bound logs/history queries.
- Prefer `QAbstractTableModel`/`QTableView` for high-volume data.
- Preserve catalog caching instead of repeated full-table scans.
- Keep financial calculations in `Decimal` in the service layer.
- Profile startup, product search and checkout before making speculative optimizations.

## Release workflow

1. Ensure CI is green on all Windows/Linux + supported Python matrices.
2. Run a fresh-data first-run setup smoke test.
3. Run a real workflow smoke test: login → shift → stock → sale → credit → payment → reports → backup.
4. Bump `ApplicationSettings.APP_VERSION` and installer/spec metadata together.
5. Build natively with `python scripts/build_release.py`.
6. Test the native artifacts on clean Windows and Linux machines.
7. Tag `v<version>` only after the smoke tests pass.
