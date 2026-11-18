CREATE TABLE Owner_Access_Recovery (
    employee_id INTEGER PRIMARY KEY REFERENCES Employee(Employee_id),
    code_digest TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    retry_after REAL NOT NULL DEFAULT 0
);
