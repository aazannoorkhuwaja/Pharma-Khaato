"""Regression coverage for the independently reproduced Phase 1 findings."""
import sqlite3
import pytest


def checkout(employee, **kwargs):
    from core.pos_service import CheckoutRequest, POSTransactionEngine
    return POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN', employee,
        [{'prod_id': 1, 'qty': 1, 'price': 15}], payment_method='Card', **kwargs))


def test_return_uses_authenticated_terminal(seeded_shop, admin_emp_id):
    from core.cash_session_service import open_session
    from core.pos_service import CheckoutRequest, POSTransactionEngine
    from core.lan_service import ShopService
    a = open_session(admin_emp_id, 100, terminal_id='A')[1]
    open_session(admin_emp_id, 100, terminal_id='B')
    sale = POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN', admin_emp_id,
        [{'prod_id': 1, 'qty': 1, 'price': 15}], terminal_id='A'))
    assert sale.success
    service = ShopService()
    token = service.login('admin', 'secret123', 'A')['token']
    result = service.call(token, 'ReturnModel', 'process',
        args=[sale.purchase_id, [{'batch_id': 1, 'qty': 1}], admin_emp_id, 'Return', 'SELLABLE'],
        kwargs={'operation_id': 'audit-terminal', 'terminal_id': 'B'}, request_id='audit-terminal-request')
    assert result[0], result
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT session_id FROM Customer_Returns WHERE purchase_id=%s', (sale.purchase_id,))
        assert cur.fetchone()[0] == a


@pytest.mark.parametrize('expiry', ['not-a-date', '2099-02-30', '20991231'])
def test_invalid_expiry_cannot_sell(seeded_shop, admin_emp_id, expiry):
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute('UPDATE Batch SET expiry_date=%s WHERE id=1', (expiry,))
    assert not checkout(admin_emp_id).success


def test_mrp_checked_at_sale(seeded_shop, admin_emp_id):
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute('UPDATE Batch SET mrp=10 WHERE id=1')
    result = checkout(admin_emp_id)
    assert not result.success and 'MRP' in result.message
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT quantity FROM Batch WHERE id=1')
        assert cur.fetchone()[0] == 100


@pytest.mark.parametrize('quantity,discount', [(1, .01), (3, .01)])
def test_zero_payout_does_not_prevent_stock_return(seeded_shop, admin_emp_id, quantity, discount):
    from core.pos_service import CheckoutRequest, POSTransactionEngine
    from core.manager_auth_service import issue_discount_approval
    from core.return_service import process_return
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute('UPDATE Products SET price=.01 WHERE id=1')
    approval = issue_discount_approval('admin', 'secret123', admin_emp_id, discount, quantity * .01)[0]
    sale = POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN', admin_emp_id,
        [{'prod_id': 1, 'qty': quantity, 'price': .01}], payment_method='Card', discount=discount,
        manager_approval_token=approval))
    assert sale.success, sale
    refunds = []
    for i in range(quantity):
        ok, result = process_return(sale.purchase_id, [{'batch_id': 1, 'qty': 1}], admin_emp_id, operation_id=f'return-{i}')
        assert ok, result
        refunds.append(result['refund_amount'])
    assert round(sum(refunds), 2) == round(quantity * .01 - discount, 2)
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT quantity FROM Batch WHERE id=1')
        assert cur.fetchone()[0] == 100
        cur.execute('SELECT COUNT(*) FROM Refund_Transaction WHERE amount<=0')
        assert cur.fetchone()[0] == 0
    assert not process_return(sale.purchase_id, [{'batch_id': 1, 'qty': 1}], admin_emp_id)[0]


def test_newer_schema_refused(fresh_db):
    from core.migration_manager import MigrationManager
    with sqlite3.connect(':memory:') as conn:
        conn.execute('CREATE TABLE schema_migrations(version TEXT PRIMARY KEY,applied_at TEXT)')
        conn.execute("INSERT INTO schema_migrations VALUES('999_future.sql','today')")
        conn.commit()
        with pytest.raises(RuntimeError, match='different application version'):
            MigrationManager.apply_migrations(conn)


def test_pack_refund_preview_uses_line_value():
    from types import SimpleNamespace
    from decimal import Decimal
    from ui.screens.returns_screen import ReturnsScreen
    screen = SimpleNamespace(current_sale={'lines': [{'batch_id':1,'line_base':1,'unit_price':.33,
        'sold_qty':3,'remaining_returnable':3}], 'gross_total':1,'already_refunded':0})
    assert ReturnsScreen._preview_refund(screen, {1:2}) == Decimal('.67')


def test_backup_rejects_missing_declared_table(seeded_shop, tmp_path):
    from core.backup_service import _validate_sqlite_database
    path = tmp_path / 'snapshot.sqlite'
    with sqlite3.connect(path) as target:
        seeded_shop.get_conn().raw_conn.backup(target)
    assert _validate_sqlite_database(str(path)) == (True, 'ok')
    with sqlite3.connect(path) as target:
        target.execute('DROP TABLE Return_Operation')
    valid, reason = _validate_sqlite_database(str(path))
    assert not valid and 'Return_Operation' in reason


@pytest.mark.parametrize('value', ['=1+1', '+1', '-cmd', '@SUM(1)', '\t=1', '  =1'])
def test_spreadsheet_formula_neutralized(value):
    from core.export_safety import spreadsheet_text
    assert spreadsheet_text(value).startswith("'")


def test_expiry_failure_is_not_empty_result(monkeypatch):
    from core import reports_service
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError('test failure')
    monkeypatch.setattr(reports_service, 'get_db', broken)
    with pytest.raises(RuntimeError, match='unavailable'):
        reports_service.get_expiry_alert_report()
    with pytest.raises(RuntimeError, match='unavailable'):
        reports_service.get_reorder_stock_report()


def test_postcommit_cash_failure_preserves_identity_and_retries_once(seeded_shop, admin_emp_id, monkeypatch):
    from core import cash_session_service as cash
    from core.local_operations import perform, pending
    def interrupted(*args):
        raise OSError('Lost response after commit')
    monkeypatch.setattr(cash, 'log_audit_event', interrupted)
    callback = lambda op: cash.open_session(admin_emp_id, 20, operation_id=op)
    with pytest.raises(RuntimeError, match='unknown'):
        perform(admin_emp_id, 'open', {'opening_cash':20}, callback)
    assert pending(admin_emp_id) is not None
    result = perform(admin_emp_id, 'open', {'opening_cash':20}, callback)
    assert result[0] and pending(admin_emp_id) is None
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT COUNT(*) FROM Cash_Register_Session')
        assert cur.fetchone()[0] == 1


def test_cumulative_refund_cents():
    from core.refund_quote import quote_refund
    from decimal import Decimal
    assert quote_refund('.02', '.03', '.01', '.01', '.01') == Decimal('0')
    assert quote_refund('.02', '.03', '.02', '.01', '.01', True) == Decimal('.01')
