-- Phase 5 Remediation: Cash Movements Ledger
-- Tracks cash in, cash out, and cash refunds for register sessions

CREATE TABLE IF NOT EXISTS Cash_Movement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES Cash_Register_Session(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES Employee(Employee_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cash_movement_session ON Cash_Movement(session_id);
