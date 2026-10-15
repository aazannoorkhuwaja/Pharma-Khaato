-- Migration 007: Customer Returns & Refund Audit Ledger
CREATE TABLE IF NOT EXISTS Customer_Returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL,
    customer_id TEXT NOT NULL DEFAULT 'WALKIN',
    employee_id INTEGER NOT NULL,
    refund_amount REAL NOT NULL,
    reason TEXT NOT NULL,
    return_date TEXT NOT NULL,
    return_time TEXT NOT NULL,
    FOREIGN KEY(purchase_id) REFERENCES Purchase(id),
    FOREIGN KEY(employee_id) REFERENCES Employee(Employee_id)
);

CREATE TABLE IF NOT EXISTS Return_Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    batch_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    restock_status TEXT NOT NULL DEFAULT 'RESTOCKED',
    FOREIGN KEY(return_id) REFERENCES Customer_Returns(id),
    FOREIGN KEY(product_id) REFERENCES Products(id),
    FOREIGN KEY(batch_id) REFERENCES Batch(id)
);

CREATE INDEX IF NOT EXISTS idx_returns_purchase ON Customer_Returns(purchase_id);
CREATE INDEX IF NOT EXISTS idx_return_items_return ON Return_Items(return_id);
