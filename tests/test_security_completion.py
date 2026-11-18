"""Security/recovery acceptance using isolated stores and deterministic concurrency."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import threading
from unittest.mock import Mock
import pytest


def test_authentication_budget_is_bounded_under_concurrency():
    from core.lan_service import AuthenticationBudget
    clock = [0.0]
    budget = AuthenticationBudget(peer_limit=3, global_limit=10, max_peers=8, clock=lambda: clock[0])
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: budget.allow('peer-one'), range(30)))
    assert sum(results) == 3
    assert sum(budget.allow(f'peer-{i}') for i in range(100)) == 7
    assert len(budget._peers) <= 8
    clock[0] = 61
    assert budget.allow('new-peer')
    assert len(budget._peers) == 1


def test_login_rate_limit_precedes_password_work(monkeypatch):
    from core.lan_service import ShopService, AuthenticationBudget, ShopAPIError
    from core import auth_service
    service = ShopService()
    service._auth_budget = AuthenticationBudget(peer_limit=1)
    checker = Mock(return_value=None)
    monkeypatch.setattr(auth_service, 'login_user', checker)
    assert service.login('a', 'pw', 'A', peer='10.0.0.2') is None
    with pytest.raises(ShopAPIError) as error:
        service.login('different-user', 'pw', 'A', peer='10.0.0.2')
    assert error.value.status == 429
    assert checker.call_count == 1


def test_per_peer_connection_cap_does_not_starve_other_peers(monkeypatch):
    from core.bounded_http import BoundedTLSHTTPServer, ThreadingHTTPServer
    server = object.__new__(BoundedTLSHTTPServer)
    server._slots = threading.BoundedSemaphore(3)
    server._peer_lock = threading.Lock()
    server._peer_limit = 1
    server._peers = {}
    server.shutdown_request = Mock()
    accepted = []
    monkeypatch.setattr(ThreadingHTTPServer, 'process_request', lambda self, request, addr: accepted.append(addr))
    server.process_request(Mock(), ('10.0.0.1', 1))
    rejected = Mock()
    server.process_request(rejected, ('10.0.0.1', 2))
    server.process_request(Mock(), ('10.0.0.2', 3))
    assert accepted == [('10.0.0.1', 1), ('10.0.0.2', 3)]
    server.shutdown_request.assert_called_once_with(rejected)
    server._release_peer('10.0.0.1')
    server._release_peer('10.0.0.2')
    assert server._peers == {}


def test_lost_lan_response_replays_one_cash_operation(seeded_shop, monkeypatch):
    import core.lan_service as lan
    service = lan.ShopService()
    token = service.login('admin', 'secret123', 'A')['token']
    original = lan._invoke_remote
    def lost_reply(invocation):
        original(invocation)
        raise OSError('Simulated response loss after service commit')
    monkeypatch.setattr(lan, '_invoke_remote', lost_reply)
    with pytest.raises(OSError):
        service.call(token, 'CashSessionModel', 'open_session', args=[1, 100], request_id='cash-replay')
    monkeypatch.setattr(lan, '_invoke_remote', original)
    result = service.call(token, 'CashSessionModel', 'open_session', args=[1, 100], request_id='cash-replay')
    assert result[0]
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT COUNT(*) FROM Cash_Register_Session')
        assert cur.fetchone()[0] == 1
        cur.execute('SELECT response_json FROM Shop_Request WHERE request_id=%s', ('cash-replay',))
        assert json.loads(cur.fetchone()[0]) == result


def test_concurrent_counter_last_unit_cannot_oversell(seeded_shop):
    from core.lan_service import ShopService
    from core.db_engine import reset_thread_connections
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute('UPDATE Products SET stock_quantity=1 WHERE id=1')
        cur.execute('UPDATE Batch SET quantity=1 WHERE id=1')
    service = ShopService()
    tokens = [service.login('admin', 'secret123', name)['token'] for name in ('A','B')]
    barrier = threading.Barrier(2)
    def checkout(i):
        from core.pos_service import CheckoutRequest
        barrier.wait()
        try:
            request = CheckoutRequest('WALKIN', 1, [{'prod_id':1,'qty':1,'price':15}], payment_method='Card', checkout_token=f'last-unit-{i}')
            from dataclasses import asdict
            return service.call(tokens[i], 'POSModel', 'process_checkout', args=[asdict(request)], request_id=f'last-unit-request-{i}')
        finally:
            reset_thread_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(checkout, (0,1)))
    assert sum(result['success'] for result in results) == 1
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT quantity FROM Batch WHERE id=1')
        assert cur.fetchone()[0] == 0
        cur.execute('SELECT COUNT(*) FROM Purchase')
        assert cur.fetchone()[0] == 1


def test_encrypted_new_host_bundle_roundtrip(seeded_shop, tmp_path):
    from scripts.recovery_bundle import export_bundle, import_bundle
    from core.path_manager import PathManager
    from core.lan_config import save_host_config
    from core.backup_trust import _digest
    save_host_config('127.0.0.1')
    config = Path(PathManager.get_config_dir())
    (config / 'pending-cash-1.json').write_text('{"operation_id":"keep-this-id"}')
    bundle = tmp_path / 'owner.pkrecovery'
    passphrase = 'owner recovery phrase 123456'
    export_bundle(bundle, 'admin', 'secret123', passphrase)
    data = bundle.read_bytes()
    assert b'keep-this-id' not in data and b'SQLite format' not in data
    target = tmp_path / 'new-host'
    import_bundle(bundle, target, passphrase)
    key = (target / 'config/recovery.key').read_bytes()
    assert _digest(target / 'data/pharmacy_db.sqlite', key) == (target / 'data/pharmacy_db.sqlite.hmac').read_text()
    assert json.loads((target / 'config/pending-cash-1.json').read_text())['operation_id'] == 'keep-this-id'
    host = json.loads((target / 'config/counter_connection.json').read_text())
    assert Path(host['key_path']).is_relative_to(target)
    assert Path(host['key_path']).is_file()
    with pytest.raises(ValueError, match='never overwritten'):
        import_bundle(bundle, target, passphrase)
    with pytest.raises(ValueError, match='Wrong recovery'):
        import_bundle(bundle, tmp_path / 'wrong-password', 'a different long password')
    assert not (tmp_path / 'wrong-password').exists()


def test_bundle_export_requires_owner(seeded_shop, tmp_path):
    from scripts.recovery_bundle import export_bundle
    with pytest.raises(PermissionError):
        export_bundle(tmp_path / 'bad.pkrecovery', 'admin', 'wrong-password', 'long recovery password')
    assert not (tmp_path / 'bad.pkrecovery').exists()


def test_bundle_rejects_path_traversal_before_extraction(tmp_path):
    from scripts.recovery_bundle import _MAGIC, _cipher, import_bundle
    import io, zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('../outside', 'bad')
    salt, nonce = os.urandom(16), os.urandom(12)
    password = 'long recovery password'
    bundle = tmp_path / 'malicious.pkrecovery'
    bundle.write_bytes(_MAGIC + salt + nonce + _cipher(password, salt).encrypt(nonce, buffer.getvalue(), _MAGIC))
    with pytest.raises(ValueError, match='entry path'):
        import_bundle(bundle, tmp_path / 'new-host', password)
    assert not (tmp_path / 'outside').exists()
    assert not (tmp_path / 'new-host').exists()


def test_staff_offboarding_revokes_existing_session_and_core_permissions(seeded_shop):
    from core.auth_service import create_employee, set_employee_active, login_user
    from core.lan_service import ShopService, ShopAPIError
    from core.permission_service import require_permission
    assert create_employee('counterstaff','secret123','Counter','Staff','Salesman',actor_id=1)[0]
    service=ShopService()
    session=service.login('counterstaff','secret123','OFFBOARD')['token']
    actor=service.session(session)['employee_id']
    assert require_permission(actor,'pos.sell')[0]
    assert not set_employee_active(actor,False,actor_id=actor)[0]
    assert set_employee_active(actor,False,actor_id=1)[0]
    assert not require_permission(actor,'pos.sell')[0]
    assert login_user('counterstaff','secret123') is None
    with pytest.raises(ShopAPIError):service.session(session)
    assert not set_employee_active(1,False,actor_id=1)[0]
    assert set_employee_active(actor,True,actor_id=1)[0]
    assert login_user('counterstaff','secret123') is not None


def test_host_recovery_does_not_use_configured_paths(seeded_shop, tmp_path):
    from core.recovery_bundle_service import export_bundle, import_bundle
    from core.path_manager import PathManager
    from core.lan_config import save_host_config
    save_host_config('127.0.0.1')
    config = Path(PathManager.get_config_dir()) / 'counter_connection.json'
    values = json.loads(config.read_text())
    values['certificate_path'] = '../../outside.pem'
    values['key_path'] = 'C:\\outside\\secret.pem'
    config.write_text(json.dumps(values))
    bundle = tmp_path / 'owner.pkrecovery'
    phrase = 'long recovery password'
    export_bundle(bundle, 'admin', 'secret123', phrase)
    target = tmp_path / 'recovered'
    import_bundle(bundle, target, phrase)
    restored = json.loads((target / 'config/counter_connection.json').read_text())
    assert restored['certificate_path'] == str(target / 'config/shop-tls/shop-certificate.pem')
    assert restored['key_path'] == str(target / 'config/shop-tls/shop-private-key.pem')
