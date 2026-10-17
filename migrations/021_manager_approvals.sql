CREATE TABLE IF NOT EXISTS Manager_Approval (
    token_hash TEXT PRIMARY KEY,
    operator_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
    manager_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
    subtotal_minor INTEGER NOT NULL,
    discount_minor INTEGER NOT NULL,
    expires_at REAL NOT NULL,
    used_at REAL
);
