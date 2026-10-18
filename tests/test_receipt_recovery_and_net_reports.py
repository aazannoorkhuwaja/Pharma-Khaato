"""Saved receipt, retry and owner-report behavior across real transactions."""
import sqlite3
import pytest


def sale(shop, employee, *, qty=2, method='Cash', customer='WALKIN'):
    from core.pos_service import CheckoutRequest, POSTransactionEngine
    import uuid
    request = CheckoutRequest(customer, employee, [{'prod_id':1,'name':'TestMed','price':15,'qty':qty}],
                              payment_method=method, checkout_token=uuid.uuid4().hex)
    result = POSTransactionEngine.process_checkout(request)
    assert result.success, result.message
    return result.purchase_id


@pytest.mark.parametrize('tender', ['Cash','Credit Card','Easypaisa','JazzCash'])
def test_receipt_keeps_real_tender_and_cashier(cash_shift, seeded_shop, admin_emp_id, tender):
    from core.receipt_service import receipt_for_sale
    purchase = sale(seeded_shop, admin_emp_id, method=tender)
    text = receipt_for_sale(purchase)['receipt_text']
    assert tender in text
    assert 'Test Admin' in text
    assert 'e.id' not in text


def test_reprint_uses_immutable_saved_content_and_never_sells_again(cash_shift, seeded_shop, admin_emp_id, monkeypatch):
    from core import receipt_service
    purchase = sale(seeded_shop, admin_emp_id)
    before = receipt_service.receipt_for_sale(purchase)['receipt_text']
    conn = seeded_shop.get_conn()
    conn.cursor().execute("UPDATE Products SET product_name='Changed name',price=99 WHERE id=1")
    conn.commit()
    sent=[]
    monkeypatch.setattr(receipt_service,'print_receipt_spooler',lambda text,*args: sent.append(text) or True)
    assert receipt_service.reprint_sale_receipt(purchase)[0]
    assert before in sent[0] and 'REPRINT' in sent[0]
    assert receipt_service.receipt_for_sale(purchase)['receipt_text'] == before
    assert conn.cursor().execute('SELECT COUNT(*) FROM Purchase').fetchone()[0] == 1
    assert conn.cursor().execute('SELECT quantity FROM Batch WHERE id=1').fetchone()[0] == 98
    with pytest.raises(sqlite3.IntegrityError):
        with seeded_shop.get_db() as (_conn,cur):
            cur.execute("UPDATE Receipt_Snapshot SET receipt_text='changed' WHERE purchase_id=%s",(purchase,))


def test_return_retry_is_one_refund_and_one_stock_restore(cash_shift, seeded_shop, admin_emp_id):
    from core.return_service import process_return, lookup_return_result
    purchase = sale(seeded_shop,admin_emp_id)
    args=(purchase,[{'batch_id':1,'qty':1}],admin_emp_id)
    first=process_return(*args,operation_id='one-physical-return')
    again=process_return(*args,operation_id='one-physical-return')
    assert first[0] and again[0]
    assert first[1]['return_id']==again[1]['return_id']
    assert lookup_return_result('one-physical-return',admin_emp_id)['return_id']==first[1]['return_id']
    cur=seeded_shop.get_conn().cursor()
    assert cur.execute('SELECT COUNT(*) FROM Customer_Returns').fetchone()[0]==1
    assert cur.execute('SELECT quantity FROM Batch WHERE id=1').fetchone()[0]==99
    assert not process_return(purchase,[{'batch_id':1,'qty':2}],admin_emp_id,operation_id='one-physical-return')[0]


def test_refunded_sale_has_explicit_gross_returns_and_net(cash_shift, seeded_shop, admin_emp_id):
    from core.return_service import process_return
    from core.reports_service import get_daily_sales_report
    purchase=sale(seeded_shop,admin_emp_id)
    assert process_return(purchase,[{'batch_id':1,'qty':2}],admin_emp_id,operation_id='full-return')[0]
    report=get_daily_sales_report()
    assert report['gross_sales']==30
    assert report['returns_total']==30
    assert report['net_sales']==0
    assert report['cash_refunds']==30


def test_read_failure_is_unavailable_not_zero(monkeypatch):
    from core import reports_service
    def unavailable(*args,**kwargs):
        raise sqlite3.OperationalError('disk unavailable')
    monkeypatch.setattr(reports_service,'get_db',unavailable)
    with pytest.raises(RuntimeError,match='unavailable'):
        reports_service.get_daily_sales_report()
    with pytest.raises(RuntimeError,match='unavailable'):
        reports_service.get_credit_collections_report()
