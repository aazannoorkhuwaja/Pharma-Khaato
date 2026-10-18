"""Supplier stock/money posts and drawer requests survive real retries."""
import pytest


def line(**changes):
    return {'product_id':1,'quantity':2,'unit_code':'base','cost_per_unit':10,
            'expiry':'12/2099','lot':'SUPPLIER-A','sale_price':15,**changes}


def test_invoice_stock_balance_and_duplicate_reference_are_atomic(seeded_shop,admin_emp_id):
    from core.supplier_service import receive_invoice,supplier_accounts
    first=receive_invoice(1,'INV-1',[line(),line(quantity=3,lot='OTHER')],admin_emp_id,
                          operation_id='invoice-once',paid_amount=10)
    assert first[0],first
    assert first[2]['total']==50 and first[2]['balance']==40
    again=receive_invoice(1,'INV-1',[line(),line(quantity=3,lot='OTHER')],admin_emp_id,
                          operation_id='invoice-once',paid_amount=10)
    assert again[0] and again[2]['invoice_id']==first[2]['invoice_id']
    assert not receive_invoice(1,'INV-1',[line()],admin_emp_id,operation_id='different-id')[0]
    cur=seeded_shop.get_conn().cursor()
    assert cur.execute('SELECT stock_quantity FROM Products WHERE id=1').fetchone()[0]==105
    assert supplier_accounts()[0]['balance']==40


def test_bad_invoice_line_rolls_back_every_line(seeded_shop,admin_emp_id):
    from core.supplier_service import receive_invoice
    result=receive_invoice(1,'BAD',[line(),line(product_id=999)],admin_emp_id,operation_id='invoice-bad')
    assert not result[0]
    cur=seeded_shop.get_conn().cursor()
    assert cur.execute('SELECT COUNT(*) FROM Supplier_Invoice').fetchone()[0]==0
    assert cur.execute('SELECT stock_quantity FROM Products WHERE id=1').fetchone()[0]==100


def test_supplier_cash_payment_return_and_retry_reconcile(cash_shift,seeded_shop,admin_emp_id):
    from core.supplier_service import receive_invoice,pay_supplier,invoice_lines,return_to_supplier,supplier_accounts
    from core.cash_session_service import get_session_cash_summary
    from core.cash_session_service import record_cash_movement
    assert record_cash_movement(cash_shift,admin_emp_id,'CASH_IN',100,'Owner cash for supplier')[0]
    assert receive_invoice(1,'CREDIT-1',[line(quantity=10)],admin_emp_id,operation_id='supplier-credit')[0]
    before=get_session_cash_summary(cash_shift)['expected_cash']
    payment=pay_supplier(1,40,admin_emp_id,operation_id='supplier-cash',payment_method='Cash from drawer')
    assert payment[0] and payment[2]['balance']==60
    assert pay_supplier(1,40,admin_emp_id,operation_id='supplier-cash',payment_method='Cash from drawer')[0]
    assert get_session_cash_summary(cash_shift)['expected_cash']==before-40
    received=invoice_lines(1)[0]
    returned=return_to_supplier(received[0],3,'Short dated stock',admin_emp_id,operation_id='supplier-return')
    assert returned[0] and returned[2]['credit']==30
    assert return_to_supplier(received[0],3,'Short dated stock',admin_emp_id,operation_id='supplier-return')[0]
    assert supplier_accounts()[0]['balance']==30
    cur=seeded_shop.get_conn().cursor()
    assert cur.execute('SELECT stock_quantity FROM Products WHERE id=1').fetchone()[0]==107


def test_supplier_payment_cannot_use_other_terminal_drawer(cash_shift,seeded_shop,admin_emp_id):
    from core.supplier_service import receive_invoice,pay_supplier
    assert receive_invoice(1,'INV-TILL',[line()],admin_emp_id,operation_id='invoice-till')[0]
    assert not pay_supplier(1,10,admin_emp_id,operation_id='wrong-drawer',payment_method='Cash from drawer',terminal_id='Another-Counter')[0]


def test_cash_open_request_replay_does_not_open_another_shift(seeded_shop,admin_emp_id):
    from core.cash_session_service import open_session,close_session
    original=open_session(admin_emp_id,100,operation_id='open-once')
    assert original[0]
    assert close_session(original[1],100,employee_id=admin_emp_id)[0]
    retry=open_session(admin_emp_id,100,operation_id='open-once')
    assert retry==original
    assert seeded_shop.get_conn().cursor().execute("SELECT COUNT(*) FROM Cash_Register_Session WHERE status='OPEN'").fetchone()[0]==0


def test_durable_cash_intent_reuses_identity_after_response_loss(seeded_shop,admin_emp_id):
    from core.local_operations import perform,pending
    seen=[]
    def unconfirmed(operation):
        seen.append(operation)
        raise ConnectionError('reply lost')
    with pytest.raises(ConnectionError):
        perform(admin_emp_id,'movement',{'amount':50},unconfirmed)
    assert pending(admin_emp_id)['operation_id']==seen[0]
    with pytest.raises(ValueError,match='pending'):
        perform(admin_emp_id,'movement',{'amount':60},lambda op:(True,'wrong'))
    assert perform(admin_emp_id,'movement',{'amount':50},lambda op:(op==seen[0],'confirmed'))[0]
    assert pending(admin_emp_id) is None
