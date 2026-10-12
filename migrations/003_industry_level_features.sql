-- Migration 003: Enterprise & Industry Level Features
-- Audit Logging, Suspended/Hold Sales, and Pharmacy System Settings

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

-- Default Settings
INSERT OR IGNORE INTO Pharmacy_Settings (setting_key, setting_value) VALUES
('pharmacy_name', 'Pharma-Khaato Surgical & Retail Pharmacy'),
('pharmacy_address', 'Main Khyber Road, Peshawar, Pakistan'),
('pharmacy_phone', '+92-91-5840000'),
('drug_license_no', 'KPK-DRUG-LIC-88492'),
('ntn_number', '9482019-3'),
('receipt_footer', 'Thank you for choosing Pharma-Khaato! Medicines returnable within 7 days with valid receipt.');
