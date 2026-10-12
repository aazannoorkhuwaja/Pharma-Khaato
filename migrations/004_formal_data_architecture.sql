-- ============================================================
-- Migration 004: Formal Application Data Architecture & Pharmacy Settings
-- ============================================================

-- Legacy column additions for Products table if missing
ALTER TABLE Products ADD COLUMN barcode TEXT;
ALTER TABLE Products ADD COLUMN sku TEXT;
ALTER TABLE Products ADD COLUMN generic_name TEXT;
ALTER TABLE Products ADD COLUMN company TEXT;
ALTER TABLE Products ADD COLUMN category TEXT;
ALTER TABLE Products ADD COLUMN formula TEXT;
ALTER TABLE Products ADD COLUMN dosage_form TEXT;
ALTER TABLE Products ADD COLUMN strength TEXT;
ALTER TABLE Products ADD COLUMN pack_size INTEGER DEFAULT 1;
ALTER TABLE Products ADD COLUMN rack_location TEXT;
ALTER TABLE Products ADD COLUMN min_stock INTEGER DEFAULT 5;

-- Pharmacy Settings Key-Value Table
CREATE TABLE IF NOT EXISTS Pharmacy_Settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL
);

-- Seed initial default pharmacy settings
INSERT OR IGNORE INTO Pharmacy_Settings (setting_key, setting_value) VALUES
('pharmacy_name', 'Pharma-Khaato Pharmacy'),
('slogan', 'Counter & Surgical Care POS'),
('address', 'Main Healthcare Boulevard'),
('phone', 'Customer Care Line'),
('email', 'info@pharmakhaato.com'),
('license_number', 'NOT_CONFIGURED'),
('ntn_number', 'NOT_CONFIGURED'),
('tax_number', 'NOT_CONFIGURED'),
('receipt_footer', 'Thank you for trusting Pharma-Khaato.'),
('default_tax_rate', '0.10'),
('near_expiry_days', '30');

-- Indexes for performance & barcode lookup
CREATE INDEX IF NOT EXISTS idx_products_barcode ON Products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_sku ON Products(sku);
CREATE INDEX IF NOT EXISTS idx_products_generic ON Products(generic_name);
