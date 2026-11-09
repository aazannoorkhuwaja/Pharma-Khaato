"""Read-only reference batch browser: filters, pagination and transport policy."""
from datetime import timedelta


def test_batch_browser_filters_keep_expired_and_blocked_distinct(seeded_shop):
    from core.business_time import business_date
    from core.inventory_query_service import batch_browser
    conn=seeded_shop.get_conn();cur=conn.cursor()
    today=business_date()
    cur.execute('UPDATE Batch SET lot_number=%s,expiry_date=%s WHERE id=1',('NEAR', (today+timedelta(days=5)).isoformat()))
    for lot,expiry,status in [('OLD',(today-timedelta(days=1)).isoformat(),'SELLABLE'),('HOLD',(today+timedelta(days=60)).isoformat(),'QUARANTINED')]:
        cur.execute('INSERT INTO Batch(product_id,number_of_product,quantity,expiry_date,manufacture_Date,supplier_id,lot_number,stock_status) VALUES(1,%s,10,%s,%s,1,%s,%s)',(lot,expiry,today.isoformat(),lot,status))
    conn.commit()
    result=batch_browser()
    assert result['count']==3
    assert result['counts']=={'near':1,'expired':1,'blocked':1}
    assert [row['lot'] for row in batch_browser(expiry='expired')['rows']]==['OLD']
    assert [row['lot'] for row in batch_browser(stock_status='QUARANTINED')['rows']]==['HOLD']
    assert batch_browser(term="' OR 1=1 --")['count']==0
    assert batch_browser(term='NEAR',supplier_id=1)['count']==1
    assert batch_browser(term='NEAR',supplier_id=999)['count']==0
    assert batch_browser(limit=1,offset=1)['rows'][0]['lot']=='NEAR'
    cur.execute('SELECT SUM(quantity) FROM Batch')
    assert cur.fetchone()[0]==120


def test_batch_browser_remote_operation_is_read_only():
    from core.lan_service import OPERATIONS
    assert OPERATIONS['InventoryModel']['batch_browser']==('inventory.read',False)


def test_batch_browser_service_enforces_inventory_read(seeded_shop, admin_emp_id):
    import pytest
    from core.auth_service import create_employee
    from core.lan_service import ShopService, ShopAPIError
    assert create_employee('till', 'counterpass', 'Test', 'Cashier', 'Salesman', actor_id=admin_emp_id)[0]
    service=ShopService()
    owner=service.login('admin','secret123','Owner-Counter')
    result=service.call(owner['token'],'InventoryModel','batch_browser',kwargs={'term':'TestMed'})
    assert result['count']==1
    cashier=service.login('till','counterpass','Sales-Counter')
    with pytest.raises(ShopAPIError) as caught:
        service.call(cashier['token'],'InventoryModel','batch_browser')
    assert caught.value.status==403
