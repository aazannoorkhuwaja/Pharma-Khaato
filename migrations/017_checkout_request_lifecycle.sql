-- Transaction-coupled checkout request lifecycle.
-- The trigger completes the idempotency request in the same commit as Purchase,
-- eliminating the commit/acknowledgement crash window.

CREATE TABLE IF NOT EXISTS Checkout_Request (
    token TEXT PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'COMPLETED', 'CANCELLED')),
    purchase_id INTEGER UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES Employee(Employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (purchase_id) REFERENCES Purchase(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_checkout_request_employee_status
    ON Checkout_Request(employee_id, status, updated_at DESC);

CREATE TRIGGER IF NOT EXISTS purchase_checkout_request_ai
AFTER INSERT ON Purchase
WHEN NEW.checkout_token IS NULL
BEGIN
    UPDATE Purchase
    SET checkout_token = (
        SELECT token FROM Checkout_Request
        WHERE employee_id = NEW.employee_id AND status = 'PENDING'
        ORDER BY updated_at DESC LIMIT 1
    )
    WHERE id = NEW.id;

    UPDATE Checkout_Request
    SET status = 'COMPLETED', purchase_id = NEW.id, updated_at = datetime('now')
    WHERE token = (SELECT checkout_token FROM Purchase WHERE id = NEW.id)
      AND status = 'PENDING';
END;
