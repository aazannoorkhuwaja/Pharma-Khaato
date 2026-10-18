-- Preserve existing customer references and all historical foreign keys.
ALTER TABLE Customers ADD COLUMN display_name TEXT NOT NULL DEFAULT '';
ALTER TABLE Customers ADD COLUMN phone TEXT NOT NULL DEFAULT '';
ALTER TABLE Customers ADD COLUMN cnic TEXT;
UPDATE Customers SET display_name = trim(first_name || ' ' || last_name) WHERE display_name = '';
UPDATE Customers SET cnic = id_card_number
 WHERE length(id_card_number) = 13 AND id_card_number NOT GLOB '*[^0-9]*';
CREATE INDEX IF NOT EXISTS idx_customer_phone ON Customers(phone);
CREATE INDEX IF NOT EXISTS idx_customer_cnic_optional ON Customers(cnic);
CREATE TABLE IF NOT EXISTS Credit_Payment_Operation (
    operation_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES Customers(id_card_number),
    employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
    amount REAL NOT NULL CHECK(amount > 0),
    payment_method TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    ledger_id INTEGER,
    balance_after REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
ALTER TABLE Credit_Payment ADD COLUMN operation_id TEXT REFERENCES Credit_Payment_Operation(operation_id);
CREATE INDEX IF NOT EXISTS idx_credit_payment_operation ON Credit_Payment(operation_id);
CREATE TABLE IF NOT EXISTS Credit_Payment_Reversal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL UNIQUE REFERENCES Credit_Payment(id),
    operation_id TEXT NOT NULL UNIQUE,
    employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
    session_id INTEGER REFERENCES Cash_Register_Session(id),
    amount REAL NOT NULL CHECK(amount > 0),
    payment_method TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_credit_reversal_time ON Credit_Payment_Reversal(created_at);
