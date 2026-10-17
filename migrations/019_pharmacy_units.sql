-- Quantities remain canonical whole base units. Existing stock is not converted.
ALTER TABLE Products ADD COLUMN base_unit TEXT NOT NULL DEFAULT 'unit';
ALTER TABLE Products ADD COLUMN units_per_strip INTEGER NOT NULL DEFAULT 1;
ALTER TABLE Products ADD COLUMN units_per_box INTEGER NOT NULL DEFAULT 1;

ALTER TABLE Batch ADD COLUMN lot_number TEXT;
ALTER TABLE Batch ADD COLUMN expiry_precision TEXT NOT NULL DEFAULT 'DAY';
ALTER TABLE Batch ADD COLUMN cost_price REAL;
ALTER TABLE Batch ADD COLUMN sale_price REAL;
ALTER TABLE Batch ADD COLUMN mrp REAL;
ALTER TABLE Batch ADD COLUMN stock_status TEXT NOT NULL DEFAULT 'SELLABLE';
ALTER TABLE Batch ADD COLUMN invoice_reference TEXT;
ALTER TABLE Batch ADD COLUMN received_at TEXT;

CREATE TABLE IF NOT EXISTS Product_Code (
    code TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL,
    unit_code TEXT NOT NULL DEFAULT 'base' CHECK(unit_code IN ('base','strip','box')),
    FOREIGN KEY(product_id) REFERENCES Products(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_product_code_product ON Product_Code(product_id);

-- Preserve ambiguous legacy codes for review rather than choosing a medicine.
INSERT OR IGNORE INTO Product_Code(code,product_id,unit_code)
SELECT code,MIN(product_id),'base' FROM (
    SELECT TRIM(barcode) AS code,id AS product_id FROM Products WHERE TRIM(COALESCE(barcode,'')) <> ''
    UNION ALL SELECT TRIM(sku),id FROM Products WHERE TRIM(COALESCE(sku,'')) <> ''
    UNION ALL SELECT TRIM(alternate_barcode),id FROM Products WHERE TRIM(COALESCE(alternate_barcode,'')) <> ''
) GROUP BY code HAVING COUNT(DISTINCT product_id)=1;

CREATE TABLE IF NOT EXISTS Stock_Operation (
    operation_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    batch_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES Batch(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS Stock_Movement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    batch_id INTEGER NOT NULL,
    quantity_delta INTEGER NOT NULL CHECK(quantity_delta <> 0),
    movement_type TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    employee_id INTEGER,
    operation_key TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES Products(id) ON DELETE RESTRICT,
    FOREIGN KEY(batch_id) REFERENCES Batch(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_stock_movement_batch ON Stock_Movement(batch_id,id);
CREATE INDEX IF NOT EXISTS idx_stock_movement_product ON Stock_Movement(product_id,id);
INSERT INTO Stock_Movement(product_id,batch_id,quantity_delta,movement_type,reason,created_at)
SELECT product_id,id,quantity,'OPENING','Stock recorded before movement ledger',datetime('now')
FROM Batch WHERE quantity <> 0;

-- A single threshold now drives the catalog and reorder report.
UPDATE Products SET reorder_level=min_stock;
CREATE TRIGGER IF NOT EXISTS products_reorder_insert AFTER INSERT ON Products
BEGIN
    UPDATE Products SET reorder_level=NEW.min_stock WHERE id=NEW.id;
END;
CREATE TRIGGER IF NOT EXISTS products_reorder_update AFTER UPDATE OF min_stock ON Products
BEGIN
    UPDATE Products SET reorder_level=NEW.min_stock WHERE id=NEW.id;
END;
CREATE INDEX IF NOT EXISTS idx_batch_sellable ON Batch(product_id,stock_status,expiry_date,quantity);
