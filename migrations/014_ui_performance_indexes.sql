-- Navigation/read-path indexes for real-world catalog and ledger growth.
-- All are additive and safe to apply to existing installations.

CREATE INDEX IF NOT EXISTS idx_products_active_name
    ON Products(is_active, product_name);

CREATE INDEX IF NOT EXISTS idx_products_barcode_active
    ON Products(barcode, is_active);

CREATE INDEX IF NOT EXISTS idx_products_sku_active
    ON Products(sku, is_active);

CREATE INDEX IF NOT EXISTS idx_products_alt_barcode_active
    ON Products(alternate_barcode, is_active);

-- Product lookup repeatedly asks for the earliest non-expired batch and total
-- sellable quantity for one product. Keep product/expiry/quantity together.
CREATE INDEX IF NOT EXISTS idx_batch_product_expiry_quantity
    ON Batch(product_id, expiry_date, quantity);

-- Expiry/FEFO screens start from date and then join back to the product.
CREATE INDEX IF NOT EXISTS idx_batch_expiry_product_quantity
    ON Batch(expiry_date, product_id, quantity);

-- Open-credit screens only need rows that still have a balance. A partial
-- index keeps the hot working set small even after years of cleared history.
CREATE INDEX IF NOT EXISTS idx_khatoo_open_recent
    ON Customer_Khatoo(id DESC)
    WHERE amount_due > 0;

CREATE INDEX IF NOT EXISTS idx_customer_name_order
    ON Customers(first_name, last_name);
