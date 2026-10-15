# Pharma-Khaato Architecture

Pharma-Khaato is an offline-first, cross-platform pharmacy POS for Windows and Linux. The desktop client is implemented with PySide6; the backend is a Qt-free Python service/data stack backed by SQLite in WAL mode.

## MVC Design

```text
main.py
└── View / desktop client (ui/)
    ├── app/                 application shell, routing, session state
    ├── screens/             POS, customers, khatoo, inventory, reports, settings
    ├── widgets/             reusable presentation components
    └── theme/               theme tokens and accessibility scaling
          │
          ▼
└── Controllers (controllers/)
    ├── application_controller.py
    ├── auth_controller.py
    ├── pos_controller.py
    ├── customer_controller.py
    ├── inventory_controller.py
    ├── cash_session_controller.py
    ├── reports_controller.py
    └── settings_controller.py
          │
          ▼
└── Models (models/)
    └── services.py          Qt-free model facades
          │
          ▼
└── Backend services (core/)
    ├── db_engine.py         SQLite WAL, transactions, thread-local connections
    ├── auth_service.py      credential hashing, lockout, audit events
    ├── pos_service.py       checkout validation, FEFO allocation, totals, writes
    ├── customer_service.py  customers, khatoo, debt aging
    ├── inventory_service.py products, batches, suppliers
    ├── reports_service.py   reporting queries
    ├── backup_service.py    online SQLite snapshots
    ├── health_service.py    cross-platform startup diagnostics
    └── path_manager.py      Windows/Linux writable user-data locations
```

The architectural rule is intentionally strict: **views do not import `core` services directly**. They call controllers, controllers coordinate one or more models, and the model facades own access to backend services. `tests/test_mvc_architecture.py` enforces this boundary.

## Frontend / Backend Separation

The **frontend** is the PySide6 desktop interface. It owns user interaction, validation hints, accessibility behavior, keyboard shortcuts, navigation, and presentation state.

The **backend** is the `models/` + `core/` stack. It has no dependency on widgets or Qt event-loop behavior and owns database access, transactions, authentication, stock allocation, cash sessions, khatoo accounting, reporting, backup/restore, and audit logging.

The default product intentionally stays offline/local rather than exposing a network server. This reduces deployment complexity and attack surface for a counter POS while preserving a clean client/backend contract through MVC controllers.

## Checkout Pipeline

`core.pos_service` remains the authoritative transaction boundary:

1. Checkout re-entrancy and process lock.
2. Identity normalization.
3. Input and inventory validation.
4. FEFO multi-batch allocation.
5. Decimal-based subtotal, discount, tax, and total calculations.
6. Khatoo credit-limit enforcement.
7. Conditional stock decrements and all sale/ledger writes inside one transaction.
8. Rollback on any failure.

## Security Model

- PBKDF2-HMAC-SHA256 password hashing with a versioned iteration count (new hashes use 600,000 iterations).
- Older PBKDF2/SHA-256 hashes remain verifiable and are transparently upgraded after successful login.
- Persistent brute-force lockout in the database.
- Parameterized SQL throughout business services.
- Role-based navigation and manager authorization for policy-sensitive actions.
- Rotating logs, audit events, and process-wide uncaught exception logging.
- User data lives outside the installation directory.

## Concurrency and Reliability

- Thread-local SQLite connections.
- `journal_mode=WAL` and a 15-second busy timeout.
- Atomic database transactions with rollback.
- Online backup through SQLite's backup API.
- Database migrations applied once per process/database path.
- Graceful thread-local database cleanup on application shutdown.

## Cross-platform Data Paths

| Platform | User data root |
|---|---|
| Windows | `%LOCALAPPDATA%\Pharma-Khaato\` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/pharma-khaato/` |

Subdirectories include `data/`, `backups/`, `receipts/`, `logs/`, `exports/`, and `config/`.
