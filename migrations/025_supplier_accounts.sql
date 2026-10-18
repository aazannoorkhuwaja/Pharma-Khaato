CREATE TABLE IF NOT EXISTS Supplier_Invoice (
 id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL REFERENCES Supplier(id),
 reference TEXT NOT NULL, invoice_date TEXT NOT NULL, total_minor INTEGER NOT NULL CHECK(total_minor>=0),
 employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
 UNIQUE(supplier_id,reference)
);
CREATE TABLE IF NOT EXISTS Supplier_Invoice_Line (
 id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES Supplier_Invoice(id),
 batch_id INTEGER NOT NULL REFERENCES Batch(id), quantity INTEGER NOT NULL CHECK(quantity>0),
 total_minor INTEGER NOT NULL CHECK(total_minor>=0)
);
CREATE TABLE IF NOT EXISTS Supplier_Payment (
 id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL REFERENCES Supplier(id),
 invoice_id INTEGER REFERENCES Supplier_Invoice(id), amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
 payment_method TEXT NOT NULL, employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
 session_id INTEGER REFERENCES Cash_Register_Session(id), created_at TEXT NOT NULL, note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS Supplier_Return (
 id INTEGER PRIMARY KEY, invoice_line_id INTEGER NOT NULL REFERENCES Supplier_Invoice_Line(id),
 quantity INTEGER NOT NULL CHECK(quantity>0), credit_minor INTEGER NOT NULL CHECK(credit_minor>=0),
 employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id), created_at TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Supplier_Operation (
 operation_id TEXT PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES Employee(Employee_id),
 fingerprint TEXT NOT NULL, result_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_supplier_invoice_date ON Supplier_Invoice(supplier_id,id);
CREATE INDEX IF NOT EXISTS idx_supplier_payment_date ON Supplier_Payment(supplier_id,id);
