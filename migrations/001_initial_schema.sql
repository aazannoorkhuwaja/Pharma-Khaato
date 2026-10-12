-- Migration 001: Initial Schema Definition
-- Creates core tables: Employee, Customers, Supplier, Products, Batch, Purchase, Sales_details, Receipt, Customer_Khatoo

CREATE TABLE IF NOT EXISTS Employee (
    Employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    First_name TEXT NOT NULL,
    Last_name TEXT NOT NULL,
    occupation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Customers (
    id_card_number TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    Email_Address TEXT,
    city TEXT,
    registration_date TEXT
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
    product_name TEXT UNIQUE NOT NULL,
    price REAL NOT NULL,
    stock_quantity INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    expiry_date TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES Products(id),
    FOREIGN KEY(supplier_id) REFERENCES Supplier(id)
);

CREATE TABLE IF NOT EXISTS Purchase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number_of_products INTEGER NOT NULL,
    total_price REAL NOT NULL,
    price_with_tax REAL NOT NULL,
    customer_id TEXT,
    employee_id INTEGER NOT NULL,
    payment_method TEXT DEFAULT 'Cash',
    discount_amount REAL DEFAULT 0.0,
    FOREIGN KEY(customer_id) REFERENCES Customers(id_card_number),
    FOREIGN KEY(employee_id) REFERENCES Employee(Employee_id)
);

CREATE TABLE IF NOT EXISTS Sales_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL,
    batch_id INTEGER NOT NULL,
    Quantity INTEGER NOT NULL,
    FOREIGN KEY(purchase_id) REFERENCES Purchase(id),
    FOREIGN KEY(batch_id) REFERENCES Batch(id)
);

CREATE TABLE IF NOT EXISTS Receipt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printing_date TEXT NOT NULL,
    time TEXT NOT NULL,
    purchase_id INTEGER UNIQUE NOT NULL,
    number_of_items INTEGER NOT NULL,
    FOREIGN KEY(purchase_id) REFERENCES Purchase(id)
);

CREATE TABLE IF NOT EXISTS Customer_Khatoo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_paid REAL DEFAULT 0.0,
    amount_due REAL NOT NULL,
    purchase_id INTEGER NOT NULL,
    customer_id TEXT NOT NULL,
    payment_method TEXT DEFAULT 'Credit',
    FOREIGN KEY(purchase_id) REFERENCES Purchase(id),
    FOREIGN KEY(customer_id) REFERENCES Customers(id_card_number)
);
