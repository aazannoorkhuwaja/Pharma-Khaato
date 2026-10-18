CREATE TABLE IF NOT EXISTS Return_Operation (
    operation_id TEXT PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    request_hash TEXT NOT NULL,
    return_id INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    FOREIGN KEY(employee_id) REFERENCES Employee(Employee_id),
    FOREIGN KEY(return_id) REFERENCES Customer_Returns(id)
);
