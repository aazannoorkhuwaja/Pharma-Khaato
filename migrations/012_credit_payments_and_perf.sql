-- Durable customer-credit repayments and hot-path indexes.

CREATE TABLE IF NOT EXISTS Credit_Payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    khatoo_id INTEGER NOT NULL,
    customer_id TEXT NOT NULL,
    employee_id INTEGER NOT NULL,
    session_id INTEGER,
    amount REAL NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL,
    paid_at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (khatoo_id) REFERENCES Customer_Khatoo(id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES Customers(id_card_number) ON DELETE RESTRICT,
    FOREIGN KEY (employee_id) REFERENCES Employee(Employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (session_id) REFERENCES Cash_Register_Session(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_credit_payment_customer_time
    ON Credit_Payment(customer_id, paid_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_payment_session_method
    ON Credit_Payment(session_id, payment_method);
CREATE INDEX IF NOT EXISTS idx_receipt_date_purchase
    ON Receipt(printing_date, purchase_id);
CREATE INDEX IF NOT EXISTS idx_purchase_employee_payment
    ON Purchase(employee_id, payment_method);
CREATE INDEX IF NOT EXISTS idx_khatoo_open_customer
    ON Customer_Khatoo(customer_id, amount_due);

-- Migration 008 created the FTS table/triggers but did not backfill products
-- that existed before the migration. Insert only rows that are truly missing.
INSERT INTO product_fts(product_id, product_name, formula, generic_name, brand_name)
SELECT p.id,
       p.product_name,
       COALESCE(p.formula, ''),
       COALESCE(p.generic_name, ''),
       COALESCE(p.brand_name, '')
FROM Products p
WHERE NOT EXISTS (
    SELECT 1 FROM product_fts f WHERE CAST(f.product_id AS INTEGER) = p.id
);
