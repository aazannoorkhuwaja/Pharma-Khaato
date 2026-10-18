-- Only the shop host opens SQLite; counters use authenticated HTTPS.
CREATE TABLE IF NOT EXISTS Shop_Session (
    token_hash TEXT PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
    terminal_id TEXT NOT NULL,
    password_revision TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shop_session_expiry ON Shop_Session(expires_at);
CREATE TABLE IF NOT EXISTS Shop_Request (
    request_id TEXT PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
    terminal_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    response_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
