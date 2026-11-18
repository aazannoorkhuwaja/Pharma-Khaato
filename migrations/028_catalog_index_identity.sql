-- One index row per product. Money projection updates must not duplicate FTS rows.
DROP TRIGGER IF EXISTS fts_products_ai;
DROP TRIGGER IF EXISTS fts_products_au;
CREATE TRIGGER fts_products_ai AFTER INSERT ON Products BEGIN
    INSERT OR REPLACE INTO product_fts(rowid,product_id,product_name,formula,generic_name,brand_name)
    VALUES(new.id,new.id,new.product_name,COALESCE(new.formula,''),COALESCE(new.generic_name,''),COALESCE(new.brand_name,''));
END;
CREATE TRIGGER fts_products_au AFTER UPDATE OF product_name,formula,generic_name,brand_name ON Products BEGIN
    DELETE FROM product_fts WHERE product_id=old.id;
    INSERT OR REPLACE INTO product_fts(rowid,product_id,product_name,formula,generic_name,brand_name)
    VALUES(new.id,new.id,new.product_name,COALESCE(new.formula,''),COALESCE(new.generic_name,''),COALESCE(new.brand_name,''));
END;
DELETE FROM product_fts;
INSERT INTO product_fts(rowid,product_id,product_name,formula,generic_name,brand_name)
SELECT id,id,product_name,COALESCE(formula,''),COALESCE(generic_name,''),COALESCE(brand_name,'') FROM Products;
