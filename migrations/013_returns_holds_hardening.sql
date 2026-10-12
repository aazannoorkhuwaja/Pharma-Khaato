-- Durable held-sale lifecycle, historical line pricing, shift attribution, and refund ledger.

ALTER TABLE Hold_Sales ADD COLUMN status TEXT NOT NULL DEFAULT 'HELD';
ALTER TABLE Hold_Sales ADD COLUMN resumed_at TEXT;
ALTER TABLE Hold_Sales ADD COLUMN completed_at TEXT;
ALTER TABLE Hold_Sales ADD COLUMN updated_at TEXT;
CREATE INDEX IF NOT EXISTS idx_hold_sales_status_employee
    ON Hold_Sales(status, employee_id, id DESC);

-- Capture the exact open shift for every new sale. Historical rows are left
-- NULL because assigning them after the fact would be a guess.
ALTER TABLE Purchase ADD COLUMN session_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_purchase_session_payment
    ON Purchase(session_id, payment_method);

CREATE TRIGGER IF NOT EXISTS purchase_capture_session_ai
AFTER INSERT ON Purchase
WHEN NEW.session_id IS NULL
BEGIN
    UPDATE Purchase
    SET session_id = (
        SELECT id FROM Cash_Register_Session
        WHERE employee_id = NEW.employee_id AND status = 'OPEN'
        ORDER BY id DESC LIMIT 1
    )
    WHERE id = NEW.id;
END;

ALTER TABLE Sales_details ADD COLUMN unit_price REAL;
ALTER TABLE Sales_details ADD COLUMN line_subtotal REAL;

-- Best-effort historical backfill. Older sales did not preserve line price, so
-- existing records use the product price available during this migration.
UPDATE Sales_details
SET unit_price = COALESCE(
        unit_price,
        (SELECT p.price FROM Batch b JOIN Products p ON p.id = b.product_id
         WHERE b.id = Sales_details.batch_id)
    ),
    line_subtotal = COALESCE(
        line_subtotal,
        Quantity * (SELECT p.price FROM Batch b JOIN Products p ON p.id = b.product_id
                    WHERE b.id = Sales_details.batch_id)
    );

-- Future sales automatically capture the sale-time catalog price without
-- requiring old checkout callers to know about the new columns.
CREATE TRIGGER IF NOT EXISTS sales_details_capture_price_ai
AFTER INSERT ON Sales_details
WHEN NEW.unit_price IS NULL
BEGIN
    UPDATE Sales_details
    SET unit_price = (
            SELECT p.price FROM Batch b JOIN Products p ON p.id = b.product_id
            WHERE b.id = NEW.batch_id
        ),
        line_subtotal = NEW.Quantity * (
            SELECT p.price FROM Batch b JOIN Products p ON p.id = b.product_id
            WHERE b.id = NEW.batch_id
        )
    WHERE purchase_id = NEW.purchase_id AND batch_id = NEW.batch_id;
END;

ALTER TABLE Customer_Returns ADD COLUMN refund_method TEXT;
ALTER TABLE Customer_Returns ADD COLUMN session_id INTEGER;
ALTER TABLE Customer_Returns ADD COLUMN refund_status TEXT NOT NULL DEFAULT 'RECORDED';

CREATE TABLE IF NOT EXISTS Refund_Transaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    session_id INTEGER,
    source_credit_payment_id INTEGER,
    amount REAL NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL,
    created_at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(return_id) REFERENCES Customer_Returns(id) ON DELETE RESTRICT,
    FOREIGN KEY(employee_id) REFERENCES Employee(Employee_id) ON DELETE RESTRICT,
    FOREIGN KEY(session_id) REFERENCES Cash_Register_Session(id) ON DELETE SET NULL,
    FOREIGN KEY(source_credit_payment_id) REFERENCES Credit_Payment(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_refund_return ON Refund_Transaction(return_id);
CREATE INDEX IF NOT EXISTS idx_refund_credit_payment ON Refund_Transaction(source_credit_payment_id);
CREATE INDEX IF NOT EXISTS idx_return_purchase_date ON Customer_Returns(purchase_id, return_date);
