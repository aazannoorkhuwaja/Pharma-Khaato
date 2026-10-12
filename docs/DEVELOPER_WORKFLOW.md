# Developer Workflow

## MVC change workflow

### Frontend / View work
1. Implement presentation changes under `ui/screens`, `ui/widgets`, or `ui/theme`.
2. Keep database/business imports out of Views.
3. Route user actions through a controller.
4. Keep formatting, widget state, accessibility text, and keyboard behavior in the View.

### Controller work
1. Put cross-feature orchestration in `controllers/`.
2. Normalize UI input at the boundary where useful.
3. Coordinate multiple Models for workflows such as POS checkout.
4. Do not execute SQL in controllers.

### Backend / Model work
1. Add or expose behavior through `models/services.py`.
2. Keep models Qt-free.
3. Put transactional/database/business rules in `core/` services.
4. Use `core.db_engine.get_db()` for atomic commit/rollback behavior.

## Testing workflow

Run the full suite before merging:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

The suite includes an architecture test that fails if a View imports a `core` service directly.

For GUI-capable development machines, also run:

```bash
QT_QPA_PLATFORM=offscreen python scripts/test_gui_auto.py
```

## Security checklist

- Never commit `.env`, databases, receipts, logs, or backups.
- Never build SQL with user values via string interpolation.
- Keep credential handling in `core.auth_service`.
- Require manager authorization where policy-sensitive operations demand it.
- Avoid logging passwords, reset values, or customer-sensitive values unnecessarily.
- Treat restore/import operations as privileged administrative actions.

## Performance checklist

- Keep long-running I/O off interactive widget callbacks where possible.
- Preserve WAL mode and transaction boundaries.
- Use existing catalog caches rather than repeated full-table scans.
- Keep checkout calculations in `Decimal` where the service layer expects it.
- Prefer lazy creation of secondary screens.

## Release workflow

1. Run tests.
2. Bump `ApplicationSettings.APP_VERSION` and the Windows installer version together.
3. Build natively with `python scripts/build_release.py`.
4. Smoke-test on a clean Windows and Linux machine.
5. Tag `v<version>`; CI creates both native artifacts.
