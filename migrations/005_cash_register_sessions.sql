-- Phase 3 Migration: Cash Register Session & End-of-Day Reconciliation
-- File: migrations/005_cash_register_sessions.sql

CREATE TABLE IF NOT EXISTS Cash_Register_Session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    opened_at TEXT NOT NULL,
    opening_cash REAL NOT NULL DEFAULT 0.0,
    closed_at TEXT,
    closing_cash_actual REAL,
    expected_cash_system REAL,
    cash_discrepancy REAL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    notes TEXT,
    FOREIGN KEY (employee_id) REFERENCES Employee(Employee_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cash_session_emp_status ON Cash_Register_Session(employee_id, status);
