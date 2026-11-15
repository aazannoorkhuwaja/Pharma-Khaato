"""Regression tests for inventory search correctness and bounded stock work."""


def test_catalog_search_keeps_search_results_and_sellable_stock_correct(seeded_shop):
    from core.inventory_query_service import search_catalog_products

    rows = search_catalog_products("TestMed")
    assert rows == [(1, "TestMed", 15.0, 100, 10, "unit", 1)]

    # Non-sellable and expired stock must not inflate the displayed quantity.
    with seeded_shop.get_db() as (_conn, cur):
        cur.execute(
            "INSERT INTO Batch(product_id,number_of_product,quantity,expiry_date,manufacture_Date,supplier_id,stock_status) "
            "VALUES(1,'blocked',50,'2099-12-31','2026-01-01',1,'QUARANTINED')"
        )
    assert search_catalog_products("TestMed")[0][3] == 100


def test_catalog_search_treats_wildcards_as_literal_characters(seeded_shop):
    from core.inventory_query_service import search_catalog_products

    with seeded_shop.get_db() as (_conn, cur):
        cur.execute("UPDATE Products SET product_name=%s WHERE id=1", ("Pain 100%_Gel",))

    assert search_catalog_products("100%")
    assert search_catalog_products("%_")
    assert search_catalog_products("100X") == []
    assert search_catalog_products("_")


def test_inventory_read_indexes_are_applied_by_migrations(fresh_db):
    with fresh_db.get_db() as (_conn, cur):
        cur.execute("PRAGMA index_list('Batch')")
        batch_indexes = {row[1] for row in cur.fetchall()}
        cur.execute("PRAGMA index_list('Supplier')")
        supplier_indexes = {row[1] for row in cur.fetchall()}

    assert "idx_batch_status_expiry_id" in batch_indexes
    assert "idx_supplier_name_id" in supplier_indexes
