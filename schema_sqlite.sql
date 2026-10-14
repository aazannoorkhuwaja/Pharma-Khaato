-- ============================================================
-- Pharma-Khaato SQLite Schema & Default Seed Data (Embedded Engine)
-- ============================================================

CREATE TABLE IF NOT EXISTS Customers (
    id_card_number TEXT NOT NULL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    Email_Address TEXT NOT NULL DEFAULT 'N/A',
    city TEXT NOT NULL DEFAULT 'N/A',
    registration_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Employee (
    Employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    First_name TEXT NOT NULL,
    Last_name TEXT NOT NULL,
    occupation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Supplier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    supplier_company_name TEXT NOT NULL,
    Email_address TEXT NOT NULL,
    phone_number TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    company_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    min_stock INTEGER NOT NULL DEFAULT 10,
    formula TEXT NOT NULL DEFAULT 'N/A',
    barcode TEXT,
    alternate_barcode TEXT,
    sku TEXT,
    generic_name TEXT,
    brand_name TEXT,
    dosage_form TEXT DEFAULT 'Tablet',
    strength TEXT DEFAULT 'N/A',
    pack_size INTEGER DEFAULT 1,
    manufacturer TEXT DEFAULT 'N/A',
    rack_location TEXT DEFAULT 'Unassigned',
    max_stock_level INTEGER DEFAULT 500,
    reorder_level INTEGER DEFAULT 20,
    requires_prescription INTEGER DEFAULT 0,
    tax_rate REAL DEFAULT 0.0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS Batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number_of_product INTEGER NOT NULL,
    expiry_date TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    manufacture_Date TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Purchase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number_of_products INTEGER NOT NULL,
    total_price REAL NOT NULL,
    price_with_tax REAL NOT NULL,
    customer_id TEXT NOT NULL,
    employee_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0.00,
    FOREIGN KEY (customer_id) REFERENCES Customers(id_card_number) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES Employee(Employee_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Receipt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printing_date TEXT NOT NULL,
    time TEXT NOT NULL,
    purchase_id INTEGER NOT NULL,
    number_of_items INTEGER NOT NULL,
    FOREIGN KEY (purchase_id) REFERENCES Purchase(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Customer_Khatoo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_paid REAL NOT NULL DEFAULT 0.00,
    amount_due REAL NOT NULL DEFAULT 0.00,
    purchase_id INTEGER NOT NULL,
    customer_id TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES Customers(id_card_number) ON DELETE CASCADE,
    FOREIGN KEY (purchase_id) REFERENCES Purchase(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Sales_details (
    purchase_id INTEGER NOT NULL,
    batch_id INTEGER NOT NULL,
    Quantity INTEGER NOT NULL,
    PRIMARY KEY (purchase_id, batch_id),
    FOREIGN KEY (purchase_id) REFERENCES Purchase(id) ON DELETE CASCADE,
    FOREIGN KEY (batch_id) REFERENCES Batch(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Audit_Log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS Hold_Sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hold_time TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    employee_id INTEGER NOT NULL,
    cart_json TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS Pharmacy_Settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL
);

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

-- Default Walk-in Customer Record
INSERT OR IGNORE INTO Customers (id_card_number, first_name, last_name, Email_Address, city, registration_date) VALUES
('GUEST_WALK_IN', 'Walk-in', 'Guest', 'N/A', 'N/A', '2026-01-01'),
('WALKIN', 'Walk-in', 'Customer', 'N/A', 'N/A', '2026-01-01');

INSERT OR IGNORE INTO Pharmacy_Settings (setting_key, setting_value) VALUES
('pharmacy_name', 'Pharma-Khaato POS'),
('slogan', 'NOT_CONFIGURED'),
('address', 'NOT_CONFIGURED'),
('phone', 'NOT_CONFIGURED'),
('email', 'NOT_CONFIGURED'),
('license_number', 'NOT_CONFIGURED'),
('ntn_number', 'NOT_CONFIGURED'),
('tax_number', 'NOT_CONFIGURED'),
('receipt_footer', 'NOT_CONFIGURED'),
('default_tax_rate', '0.00'),
('near_expiry_days', '30');

-- High Performance Indexing Strategy
CREATE INDEX IF NOT EXISTS idx_products_name ON Products(product_name);
CREATE INDEX IF NOT EXISTS idx_products_cat ON Products(category);
CREATE INDEX IF NOT EXISTS idx_products_form ON Products(formula);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON Products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_sku ON Products(sku);
CREATE INDEX IF NOT EXISTS idx_products_generic ON Products(generic_name);
CREATE INDEX IF NOT EXISTS idx_batch_exp ON Batch(expiry_date, quantity);
CREATE INDEX IF NOT EXISTS idx_batch_prod ON Batch(product_id);
CREATE INDEX IF NOT EXISTS idx_customers_cnic ON Customers(id_card_number);
CREATE INDEX IF NOT EXISTS idx_customers_name ON Customers(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_khatoo_cust ON Customer_Khatoo(customer_id);
