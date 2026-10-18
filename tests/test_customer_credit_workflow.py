"""Real account workflows: minimal identity, one handover, retries and corrections."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import uuid

import pytest


def _account():
    from core.customer_service import create_customer
    ok,message,ref=create_customer('Ahmed Ali',phone='+92 300 1234567',area='Old Bazaar')
    assert ok,message
    return ref


def _sale(ref,employee,qty):
    from core.pos_service import confirm_sale
    ok,message=confirm_sale(ref,employee,[{'prod_id':1,'name':'TestMed','price':15,'qty':qty}],payment_method='Khatoo Credit')
    assert ok,message
    return int(message.split('Sale #')[1].split(' ')[0])


def test_name_only_customer_and_normalized_optional_identity(seeded_shop):
    from core.customer_service import create_customer,validate_cnic,normalize_phone,resolve_customer_ref
    from core.customer_directory_service import search_customers
    ok,message,ref=create_customer('احمد',area='بازار')
    assert ok,message
    assert ref.startswith('CUST_')
    assert search_customers('احمد بازار')[0][0]==ref
    assert resolve_customer_ref(ref)==ref
    assert validate_cnic('٣٥٢٠٢-١٢٣٤٥٦٧-١')=='3520212345671'
    assert normalize_phone('۰۰۹۲ ۳۰۰ ۱۲۳۴۵۶۷')=='03001234567'
    ok,_,cnic_ref=create_customer('Ahmed Ali',cnic='٣٥٢٠٢١٢٣٤٥٦٧١')
    assert ok and cnic_ref=='3520212345671'
    assert resolve_customer_ref('35202-1234567-1')==cnic_ref
    assert not create_customer('Duplicate',cnic='3520212345671')[0]
    assert not create_customer('Invalid',cnic='123')[0]
    assert not create_customer('Invalid',phone='hello')[0]


def test_full_name_tokens_phone_area_and_search_wildcards(seeded_shop):
    from core.customer_directory_service import search_customers
    from core.credit_query_service import load_open_credit
    ref=_account()
    for text in ['Ahmed Ali','ali AHMED','0300 1234567','+92 300 1234567','Old Bazaar']:
        assert search_customers(text)[0][0]==ref
    assert search_customers('%')==[]
    assert search_customers('_')==[]


def test_account_payment_spans_oldest_bills_and_retries_once(seeded_shop,admin_emp_id):
    from core.credit_payment_service import record_customer_payment,payment_receipt_text,customer_statement_text
    from core.customer_service import get_customer_total_debt
    from core.cash_session_service import open_session,get_session_cash_summary
    ref=_account();_sale(ref,admin_emp_id,2);_sale(ref,admin_emp_id,3)
    ok,session=open_session(admin_emp_id,500);assert ok
    token=uuid.uuid4().hex
    first=record_customer_payment(ref,40,admin_emp_id,operation_id=token)
    assert first[0],first
    assert first[2]['balance']==35
    second=record_customer_payment(ref,40,admin_emp_id,operation_id=token)
    assert second[0] and second[2]['already_recorded']
    assert first[2]['payment_ids']==second[2]['payment_ids']
    assert not record_customer_payment(ref,41,admin_emp_id,operation_id=token)[0]
    cur=seeded_shop.get_conn().cursor()
    cur.execute('SELECT amount_due,amount_paid FROM Customer_Khatoo WHERE customer_id=%s ORDER BY id',(ref,))
    assert cur.fetchall()==[(0.0,30.0),(35.0,10.0)]
    assert get_customer_total_debt(ref)==35
    assert get_session_cash_summary(session)['expected_cash']==540
    slip=payment_receipt_text(token)
    assert 'Ahmed Ali' in slip and '40.00' in slip and '35.00' in slip and ref not in slip
    statement=customer_statement_text(ref)
    assert 'CURRENT AMOUNT DUE: Rs. 35.00' in statement


def test_overlapping_collections_preserve_balance_and_payment_sum(seeded_shop,admin_emp_id):
    from core.credit_payment_service import record_customer_payment
    from core.customer_service import get_customer_total_debt
    from core.db_engine import reset_thread_connections
    ref=_account();_sale(ref,admin_emp_id,2)
    def pay(token):
        try:
            return record_customer_payment(ref,20,admin_emp_id,'Easypaisa',operation_id=token)
        finally:
            reset_thread_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(pay,[uuid.uuid4().hex,uuid.uuid4().hex]))
    assert sum(bool(result[0]) for result in results)==1
    assert get_customer_total_debt(ref)==10
    cur=seeded_shop.get_conn().cursor();cur.execute('SELECT SUM(amount) FROM Credit_Payment WHERE customer_id=%s',(ref,))
    assert cur.fetchone()[0]==20


def test_same_operation_concurrent_retry_is_one_handover(seeded_shop,admin_emp_id):
    from core.credit_payment_service import record_customer_payment
    from core.db_engine import reset_thread_connections
    ref=_account();_sale(ref,admin_emp_id,3);token=uuid.uuid4().hex
    def pay(_):
        try:return record_customer_payment(ref,10,admin_emp_id,'JazzCash',operation_id=token)
        finally:reset_thread_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(pay,range(2)))
    assert all(result[0] for result in results)
    cur=seeded_shop.get_conn().cursor();cur.execute('SELECT COUNT(*),SUM(amount) FROM Credit_Payment WHERE customer_id=%s',(ref,))
    assert cur.fetchone()==(1,10.0)


def test_owner_reversal_preserves_original_and_restores_drawer(seeded_shop,admin_emp_id):
    from core.credit_payment_service import record_customer_payment,reverse_credit_payment
    from core.cash_session_service import open_session,get_session_cash_summary
    from core.customer_service import get_customer_total_debt
    from core.auth_service import create_employee
    ref=_account();_sale(ref,admin_emp_id,2)
    _,session=open_session(admin_emp_id,500)
    result=record_customer_payment(ref,20,admin_emp_id,operation_id=uuid.uuid4().hex);assert result[0]
    payment_id=result[2]['payment_ids'][0]
    ok,_=create_employee('counter','counter123','Counter','Staff','Salesman',actor_id=admin_emp_id);assert ok
    cur=seeded_shop.get_conn().cursor();cur.execute("SELECT Employee_id FROM Employee WHERE username='counter'");cashier=cur.fetchone()[0]
    assert not reverse_credit_payment(payment_id,cashier,'wrong account',operation_id=uuid.uuid4().hex)[0]
    token=uuid.uuid4().hex
    reversed_result=reverse_credit_payment(payment_id,admin_emp_id,'wrong account',operation_id=token)
    assert reversed_result[0],reversed_result
    assert reverse_credit_payment(payment_id,admin_emp_id,'wrong account',operation_id=token)[0]
    assert not reverse_credit_payment(payment_id,admin_emp_id,'again',operation_id=uuid.uuid4().hex)[0]
    assert get_customer_total_debt(ref)==30
    assert get_session_cash_summary(session)['expected_cash']==500
    cur.execute('SELECT COUNT(*),SUM(amount) FROM Credit_Payment WHERE id=%s',(payment_id,));assert cur.fetchone()==(1,20.0)
    cur.execute('SELECT COUNT(*) FROM Credit_Payment_Reversal WHERE payment_id=%s',(payment_id,));assert cur.fetchone()[0]==1


def test_refunded_collection_cannot_be_reversed_twice(seeded_shop,admin_emp_id):
    from core.credit_payment_service import record_customer_payment,reverse_credit_payment
    from core.return_service import process_return
    from core.cash_session_service import open_session
    ref=_account();sale=_sale(ref,admin_emp_id,2);open_session(admin_emp_id,500)
    payment=record_customer_payment(ref,10,admin_emp_id,operation_id=uuid.uuid4().hex)
    assert payment[0]
    result=process_return(sale,[{'batch_id':1,'qty':2}],admin_emp_id)
    assert result[0],result
    reversed_result=reverse_credit_payment(payment[2]['payment_ids'][0],admin_emp_id,'wrong payment',operation_id=uuid.uuid4().hex)
    assert not reversed_result[0]
    assert 'refund' in reversed_result[1].lower()


def test_balance_failure_is_unavailable_and_blocks_new_credit(seeded_shop,monkeypatch):
    from core import customer_service
    ref=_account()
    @contextmanager
    def broken():
        raise sqlite3.OperationalError('disk I/O error')
        yield
    monkeypatch.setattr(customer_service,'get_db',broken)
    with pytest.raises(sqlite3.OperationalError):customer_service.get_customer_total_debt(ref)
    allowed,message=customer_service.check_customer_credit_limit(ref,10)
    assert not allowed and 'verified' in message


def test_pending_payment_survives_model_restart_and_blocks_replacement(seeded_shop,admin_emp_id):
    from models.services import KhatooModel
    ref=_account()
    draft={'customer_ref':ref,'employee_id':admin_emp_id,'operation_id':uuid.uuid4().hex,'amount':10,'customer_name':'احمد','payment_method':'Cash','note':''}
    model=KhatooModel();model.save_pending_payment(draft)
    assert KhatooModel().load_pending_payment(admin_emp_id)==draft
    replacement=dict(draft,operation_id=uuid.uuid4().hex)
    with pytest.raises(ValueError):model.save_pending_payment(replacement)
    model.clear_pending_payment(admin_emp_id,draft['operation_id'])
    assert model.load_pending_payment(admin_emp_id) is None


def test_credit_and_directory_paging_expose_totals(seeded_shop,admin_emp_id):
    from core.customer_directory_service import count_customers,search_customers_with_debt
    from core.credit_query_service import count_credit_accounts,load_credit_accounts
    for number in range(3):
        from core.customer_service import create_customer
        ok,_,ref=create_customer(f'Credit Customer {number}');assert ok
        _sale(ref,admin_emp_id,1)
    assert count_credit_accounts()==3
    assert len(load_credit_accounts(limit=2))==2
    assert len(load_credit_accounts(limit=2,offset=2))==1
    assert count_customers()>=3
    assert len(search_customers_with_debt('Credit Customer',limit=2))==2
    assert len(search_customers_with_debt('Credit Customer',limit=2,offset=2))==1
