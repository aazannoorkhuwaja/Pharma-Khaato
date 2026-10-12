-- Migration 002: Index Optimization
-- Adds high-cardinality indexes for fast POS search, FEFO lookup, and customer lookup

CREATE INDEX IF NOT EXISTS idx_batch_expiry ON Batch(product_id, expiry_date, quantity);
CREATE INDEX IF NOT EXISTS idx_cust_cnic ON Customers(id_card_number);
CREATE INDEX IF NOT EXISTS idx_cust_name ON Customers(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_purchase_cust ON Purchase(customer_id);
CREATE INDEX IF NOT EXISTS idx_khatoo_cust ON Customer_Khatoo(customer_id);
