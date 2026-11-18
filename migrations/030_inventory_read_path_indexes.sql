-- Additive indexes for the inventory read paths that filter batches by
-- sellability/expiry and repeatedly display the supplier list. Existing indexes
-- remain untouched to avoid changing established query behavior.
CREATE INDEX IF NOT EXISTS idx_batch_status_expiry_id
    ON Batch(stock_status, expiry_date, id);

CREATE INDEX IF NOT EXISTS idx_supplier_name_id
    ON Supplier(supplier_name, id);
