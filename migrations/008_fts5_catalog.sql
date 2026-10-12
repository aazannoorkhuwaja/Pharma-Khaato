-- Migration 008: SQLite FTS5 Full Text Search Index for Product Catalog
CREATE VIRTUAL TABLE IF NOT EXISTS product_fts USING fts5(
    product_id UNINDEXED,
    product_name,
    formula,
    generic_name,
    brand_name
);

CREATE TRIGGER IF NOT EXISTS fts_products_ai AFTER INSERT ON Products BEGIN
    INSERT INTO product_fts(product_id, product_name, formula, generic_name, brand_name)
    VALUES (new.id, new.product_name, COALESCE(new.formula, ''), COALESCE(new.generic_name, ''), COALESCE(new.brand_name, ''));
END;

CREATE TRIGGER IF NOT EXISTS fts_products_ad AFTER DELETE ON Products BEGIN
    DELETE FROM product_fts WHERE product_id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS fts_products_au AFTER UPDATE ON Products BEGIN
    DELETE FROM product_fts WHERE product_id = old.id;
    INSERT INTO product_fts(product_id, product_name, formula, generic_name, brand_name)
    VALUES (new.id, new.product_name, COALESCE(new.formula, ''), COALESCE(new.generic_name, ''), COALESCE(new.brand_name, ''));
END;
