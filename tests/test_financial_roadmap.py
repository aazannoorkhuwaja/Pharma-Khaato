"""Integer storage, legacy migration and synchronized multi-counter invariants."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import sqlite3
import threading
import pytest


def race(*operations):
    barrier = threading.Barrier(len(operations))
    def run(operation):
        from core.db_engine import reset_thread_connections
        barrier.wait(timeout=10)
        try:
            return operation()
        finally:
            reset_thread_connections()
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(run, operations))


def sell(employee, qty=1, token=None, customer='WALKIN', method='Card'):
    from core.pos_service import CheckoutRequest, POSTransactionEngine
    return POSTransactionEngine.process_checkout(CheckoutRequest(customer, employee,
        [{'prod_id':1,'qty':qty,'price':15,'batch_id':1}], payment_method=method, checkout_token=token))


def test_integer_storage_sums_without_float_accumulation(seeded_shop, admin_emp_id):
    from core.financial_storage import storage_reconciliation
    from core.cash_session_service import open_session
    session = open_session(admin_emp_id, 0)[1]
    with seeded_shop.get_db(immediate=True) as (_, cur):
        for i in range(1000):
            cur.execute("INSERT INTO Cash_Movement(session_id,employee_id,movement_type,amount,reason,created_at) VALUES(%s,%s,'CASH_IN',%s,'Fixture','2099-01-01')", (session,admin_emp_id,.01))
        cur.execute('SELECT SUM(amount_minor),COUNT(*) FROM Cash_Movement')
        assert cur.fetchone() == (1000,1000)
    assert storage_reconciliation(seeded_shop.get_conn().raw_conn)['ok']
    from core.cash_session_service import get_session_cash_summary
    assert get_session_cash_summary(session)['expected_cash'] == 10


def test_integer_projection_cannot_be_forged(seeded_shop):
    with pytest.raises(sqlite3.IntegrityError, match='must agree'):
        with seeded_shop.get_db(immediate=True) as (_, cur):
            cur.execute('UPDATE Products SET price_minor=1 WHERE id=1')


def test_two_counters_cannot_sell_last_unit_twice(seeded_shop, admin_emp_id):
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute('UPDATE Products SET stock_quantity=1 WHERE id=1')
        cur.execute('UPDATE Batch SET quantity=1 WHERE id=1')
    results = race(lambda:sell(admin_emp_id,token='counter-a'),lambda:sell(admin_emp_id,token='counter-b'))
    assert sum(r.success for r in results) == 1
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT quantity FROM Batch WHERE id=1')
        assert cur.fetchone()[0] == 0
        cur.execute('SELECT COUNT(*),SUM(price_with_tax_minor) FROM Purchase')
        assert cur.fetchone() == (1,1500)


def test_concurrent_checkout_replay_has_one_sale(seeded_shop, admin_emp_id):
    results = race(lambda:sell(admin_emp_id,token='same-sale'),lambda:sell(admin_emp_id,token='same-sale'))
    assert all(r.success for r in results)
    assert results[0].purchase_id == results[1].purchase_id
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT stock_quantity FROM Products WHERE id=1')
        assert cur.fetchone()[0] == 99


def test_two_payments_cannot_overcollect_credit(seeded_shop, admin_emp_id):
    from core.customer_service import create_customer
    from core.credit_payment_service import record_customer_payment
    ok, message, customer = create_customer('Concurrent credit customer')
    assert ok, message
    assert sell(admin_emp_id,qty=2,customer=customer,method='Khatoo Credit').success
    results = race(*(lambda i=i:record_customer_payment(customer,20,admin_emp_id,'Card',operation_id=f'payment-{i}') for i in range(2)))
    assert sum(r[0] for r in results) == 1
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT amount_due_minor,amount_paid_minor FROM Customer_Khatoo')
        assert cur.fetchone() == (1000,2000)


def test_concurrent_supplier_replay_posts_once(seeded_shop, admin_emp_id):
    from core.supplier_service import receive_invoice
    line={'product_id':1,'quantity':2,'unit_code':'base','cost_per_unit':10,
          'expiry':'12/2099','lot':'CONCURRENT','sale_price':15}
    operation=lambda:receive_invoice(1,'CONCURRENT',[line],admin_emp_id,operation_id='supplier-replay')
    results=race(operation,operation)
    assert all(r[0] for r in results)
    assert results[0][2]['invoice_id'] == results[1][2]['invoice_id']
    with seeded_shop.get_db() as (_,cur):
        cur.execute('SELECT stock_quantity FROM Products WHERE id=1')
        assert cur.fetchone()[0] == 102
        cur.execute('SELECT SUM(total_minor),COUNT(*) FROM Supplier_Invoice')
        assert cur.fetchone() == (2000,1)


def test_simultaneous_return_and_close_reconcile(cash_shift, seeded_shop, admin_emp_id):
    from core.cash_session_service import close_session,get_session_cash_summary
    from core.return_service import process_return
    sale=sell(admin_emp_id,method='Cash')
    assert sale.success
    returned,closed=race(lambda:process_return(sale.purchase_id,[{'batch_id':1,'qty':1}],admin_emp_id,operation_id='race-return'),
                         lambda:close_session(cash_shift,15,'Counted',employee_id=admin_emp_id,operation_id='race-close'))
    assert closed[0],closed
    summary=get_session_cash_summary(cash_shift)
    assert summary['expected_cash'] == (0 if returned[0] else 15)
    with seeded_shop.get_db() as (_,cur):
        cur.execute('SELECT COUNT(*) FROM Customer_Returns')
        assert cur.fetchone()[0] == int(returned[0])


def test_rx_flag_cannot_be_bypassed_by_direct_checkout(seeded_shop, admin_emp_id):
    with seeded_shop.get_db(immediate=True) as (_,cur):
        cur.execute('UPDATE Products SET requires_prescription=1 WHERE id=1')
    result=sell(admin_emp_id)
    assert not result.success and 'Prescription verification' in result.message


def test_legacy_backfill_records_rounding_and_checksum(fresh_db, tmp_path):
    from core.migration_manager import MigrationManager
    from core.financial_storage import register,storage_reconciliation
    root=Path(__file__).resolve().parents[1]
    with sqlite3.connect(tmp_path/'legacy.sqlite') as conn:
        register(conn)
        conn.executescript((root/'schema_sqlite.sql').read_text())
        conn.execute('CREATE TABLE schema_migrations(version TEXT PRIMARY KEY,applied_at TEXT)')
        for path in sorted((root/'migrations').glob('*.sql')):
            if path.name >= '027':
                break
            for statement in MigrationManager._split_statements(path.read_text()):
                try: conn.execute(statement)
                except sqlite3.OperationalError as exc:
                    if 'duplicate column' not in str(exc): raise
            conn.execute('INSERT INTO schema_migrations VALUES(?,?)',(path.name,'fixture'))
        conn.execute("INSERT INTO Employee VALUES(1,'legacy','test-only','Test','Admin','Admin')")
        conn.execute("INSERT INTO Cash_Register_Session(employee_id,opened_at,opening_cash,terminal_id) VALUES(1,'2000-01-01',.30000000000000004,'legacy')")
        conn.commit()
        MigrationManager.apply_migrations(conn)
        assert conn.execute('SELECT opening_cash_minor,opening_cash FROM Cash_Register_Session').fetchone() == (30,.30)
        assert conn.execute("SELECT rounded_rows FROM Money_Migration_Evidence WHERE table_name='Cash_Register_Session' AND column_name='opening_cash'").fetchone()[0] == 1
        assert storage_reconciliation(conn)['ok']
        conn.execute("UPDATE schema_migrations SET checksum='tampered' WHERE version LIKE '027%'")
        conn.commit()
        with pytest.raises(RuntimeError,match='checksum differs'):
            MigrationManager.apply_migrations(conn)


def test_ambiguous_legacy_sub_paisa_is_not_silently_rounded():
    from core.financial_storage import to_units
    with pytest.raises(ValueError, match='historical reconciliation'):
        to_units('.105',100)
    assert to_units(.1+.2,100)==30


def test_unknown_credit_result_does_not_become_cached_rejection(seeded_shop, monkeypatch):
    from core.lan_service import ShopService
    import core.lan_service as lan
    service=ShopService()
    token=service.login('admin','secret123','A')['token']
    calls=[]
    def unknown_then_complete(invocation):
        calls.append(1)
        return [False,'Unconfirmed',{'outcome':'unknown'}] if len(calls)==1 else [True,1]
    monkeypatch.setattr(lan,'_invoke_remote',unknown_then_complete)
    first=service.call(token,'CashSessionModel','open_session',args=[1,0],request_id='unknown-contract')
    assert first[2]['outcome']=='unknown'
    assert service.call(token,'CashSessionModel','open_session',args=[1,0],request_id='unknown-contract')[0]
    assert len(calls)==2


def test_unknown_nested_outcome_preserves_local_intent(seeded_shop):
    from core.local_operations import perform,pending
    result=perform(1,'receipt',{'qty':1},lambda op:(False,'Unconfirmed',{'outcome':'unknown'}),domain='stock')
    assert not result[0] and pending(1,'stock')


def test_pack_conversion_cannot_reinterpret_received_stock(seeded_shop, admin_emp_id):
    from core.inventory_service import update_product
    ok, message = update_product(1, name='TestMed', price=15, units_per_strip=10,
                                 units_per_box=100, employee_id=admin_emp_id)
    assert not ok and 'pack conversion cannot change' in message
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT units_per_strip,units_per_box,stock_quantity FROM Products WHERE id=1')
        assert cur.fetchone() == (1,1,100)


def test_copy_reconciliation_detects_ledger_and_stock_drift(cash_shift, seeded_shop, admin_emp_id, tmp_path):
    from core.cash_session_service import close_session
    from scripts.financial_reconciliation import reconcile
    assert sell(admin_emp_id, method='Cash').success
    assert close_session(cash_shift,15,employee_id=admin_emp_id)[0]
    copied = tmp_path / 'review-copy.sqlite'
    with sqlite3.connect(copied) as destination:
        seeded_shop.get_conn().raw_conn.backup(destination)
    assert reconcile(copied)['ok']
    from core.financial_storage import register
    with sqlite3.connect(copied) as conn:
        register(conn)
        conn.execute('UPDATE Products SET stock_quantity=stock_quantity+1 WHERE id=1')
        conn.execute('UPDATE Cash_Register_Session SET expected_cash_system=14 WHERE id=?',(cash_shift,))
    before = copied.read_bytes()
    report = reconcile(copied)
    assert not report['ok']
    assert {'stock_total_mismatch','closed_cash_reconciliation'} <= {r['problem'] for r in report['issues']}
    assert copied.read_bytes() == before


def test_legacy_reconciliation_reports_sub_paisa_without_migrating(tmp_path):
    from scripts.financial_reconciliation import reconcile
    source=tmp_path/'legacy-review.sqlite'
    with sqlite3.connect(source) as conn:
        conn.execute('CREATE TABLE Purchase(total_price REAL)')
        conn.execute('INSERT INTO Purchase VALUES(.105)')
    before=source.read_bytes()
    report=reconcile(source)
    assert not report['ok'] and report['review_required']
    assert any(row['problem']=='legacy_amount_requires_review' for row in report['issues'])
    assert source.read_bytes()==before
