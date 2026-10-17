"""Pharmacy pack, batch and receiving correctness on isolated databases."""
from datetime import timedelta

import pytest

from core.business_time import business_date


def make_product(*, units=True):
    from core.inventory_service import register_product
    from core.db_engine import get_conn
    ok, message = register_product(
        "Pack Medicine 500mg", 2.50, min_stock=10, base_unit="tablet",
        units_per_strip=10 if units else 1, units_per_box=100 if units else 1,
        unit_barcodes={"base":"TABLET1", **({"strip":"STRIP1","box":"BOX1"} if units else {})},
    )
    assert ok, message
    cur = get_conn().cursor()
    cur.execute("SELECT id FROM Products WHERE product_name='Pack Medicine 500mg'")
    return cur.fetchone()[0]


def receive(product_id, **kwargs):
    from core.inventory_service import add_batch
    ok, message = add_batch(product_id, 1, 2, "02/2099", unit_code="box", lot_number="LOT-A",
                            expiry_precision="MONTH", sale_price=2.5, mrp=3, **kwargs)
    assert ok, message


def test_receive_boxes_scan_strips_and_base_units(seeded_shop):
    from core.product_search_service import get_product_by_barcode
    product = make_product()
    receive(product)
    box = get_product_by_barcode("BOX1")
    strip = get_product_by_barcode("STRIP1")
    base = get_product_by_barcode("TABLET1")
    assert box[2:3] == (250.0,)
    assert box[4] == 2 and box[6]["unit_multiplier"] == 100
    assert strip[2] == 25 and strip[4] == 20
    assert base[2] == 2.5 and base[4] == 200
    assert box[5] == "2099-02-28"
    assert box[6]["lot_number"] == "LOT-A"


def test_receiving_replay_is_exactly_once_and_rejects_changed_payload(seeded_shop):
    from core import inventory_service as inv
    product = make_product()
    receive(product, operation_key="receive-once")
    receive(product, operation_key="receive-once")
    ok, message = inv.add_batch(product,1,3,"02/2099",unit_code="box",lot_number="LOT-A",
                                expiry_precision="MONTH",sale_price=2.5,mrp=3,operation_key="receive-once")
    assert not ok and "different" in message.lower()
    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT stock_quantity FROM Products WHERE id=%s",(product,))
    assert cur.fetchone()[0] == 200
    cur.execute("SELECT COUNT(*) FROM Stock_Movement WHERE product_id=%s",(product,))
    assert cur.fetchone()[0] == 1


def test_cross_namespace_codes_and_ambiguous_legacy_scan(seeded_shop):
    from core import inventory_service as inv
    from core.product_search_service import get_product_by_barcode
    assert inv.register_product("SKU Medicine",2,sku="COLLIDE")[0]
    ok, message = inv.register_product("Other Medicine",2,barcode="COLLIDE")
    assert not ok and "another product" in message
    cur=seeded_shop.get_conn().cursor()
    cur.execute("UPDATE Products SET alternate_barcode='BC1' WHERE product_name='SKU Medicine'")
    seeded_shop.get_conn().commit()
    with pytest.raises(ValueError,match="more than one"):
        get_product_by_barcode("BC1")


def test_expired_and_blocked_stock_do_not_hide_reorder_need(seeded_shop):
    from core import inventory_service as inv
    from core.inventory_query_service import catalog_snapshot
    from core.product_search_service import get_product_by_barcode
    product=make_product()
    receive(product)
    cur=seeded_shop.get_conn().cursor()
    cur.execute("UPDATE Batch SET expiry_date=%s WHERE product_id=%s",
                ((business_date()-timedelta(days=1)).isoformat(),product))
    seeded_shop.get_conn().commit()
    row=next(row for row in catalog_snapshot()["products"] if row[0]==product)
    assert row[3] == 0
    assert any(row[0]=="Pack Medicine 500mg" for row in inv.get_low_stock_products())
    assert get_product_by_barcode("BOX1") is None
    cur.execute("UPDATE Batch SET expiry_date='2099-02-28',stock_status='RECALLED' WHERE product_id=%s",(product,))
    seeded_shop.get_conn().commit()
    assert get_product_by_barcode("BOX1") is None
    cur.execute("SELECT stock_quantity FROM Products WHERE id=%s",(product,))
    assert cur.fetchone()[0] == 200


def test_stock_count_replay_stale_guard_and_condition_audit(seeded_shop):
    from core import inventory_service as inv
    product=make_product()
    receive(product)
    cur=seeded_shop.get_conn().cursor()
    cur.execute("SELECT id FROM Batch WHERE product_id=%s",(product,))
    batch=cur.fetchone()[0]
    args=dict(expected_quantity=200,stock_status="QUARANTINED",operation_key="count-once")
    assert inv.set_batch_count(batch,190,"Damaged pack",**args)[0]
    assert inv.set_batch_count(batch,190,"Damaged pack",**args)[0]
    assert not inv.set_batch_count(batch,180,"Second count",expected_quantity=200)[0]
    cur.execute("SELECT quantity,stock_status FROM Batch WHERE id=%s",(batch,))
    assert cur.fetchone() == (190,"QUARANTINED")
    cur.execute("SELECT quantity_delta FROM Stock_Movement WHERE batch_id=%s ORDER BY id",(batch,))
    assert cur.fetchall() == [(200,),(-10,)]


def test_price_edit_preserves_existing_batch_price(seeded_shop):
    from core import inventory_service as inv
    from core.product_search_service import get_product_by_barcode
    product=make_product()
    receive(product)
    details=inv.product_details(product)
    details.pop("id")
    details["price"]=4
    assert inv.update_product(product,**details)[0]
    assert get_product_by_barcode("TABLET1")[2] == 2.5


def test_unknown_manufacture_date_and_month_precision_are_preserved(seeded_shop):
    product=make_product()
    receive(product)
    cur=seeded_shop.get_conn().cursor()
    cur.execute("SELECT manufacture_Date,expiry_precision FROM Batch WHERE product_id=%s",(product,))
    assert cur.fetchone() == ("","MONTH")


def test_fractional_quantity_bad_pack_and_over_mrp_are_rejected(seeded_shop):
    from core import inventory_service as inv
    from core.unit_service import convert_quantity
    product=make_product()
    assert convert_quantity(product,3,"strip") == 30
    assert not inv.add_batch(product,1,2.9,"2099-12-31")[0]
    assert not inv.add_batch(product,1,1,"2099-12-31",sale_price=4,mrp=3)[0]
    assert not inv.register_product("Bad packs",2,units_per_strip=10,units_per_box=15)[0]
    assert not inv.add_batch(product,1,1,"2099-12-31","2100-99-99")[0]


def test_inventory_model_requires_authenticated_manager_for_mutations(seeded_shop):
    from models.services import InventoryModel
    model=InventoryModel()
    result=model.register_product("Unauthorized medicine",10)
    assert result[0] is False
