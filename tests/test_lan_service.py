"""Real TLS requests against an isolated authoritative shop database."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.lan_client import LanClient, ShopAuthorizationError, ShopConnectionError, ShopOperationError
from core.lan_service import ShopService, create_shop_server, ensure_shop_certificate


@pytest.fixture
def lan_shop(seeded_shop, admin_emp_id, tmp_path):
    from core.auth_service import create_employee
    from core.permission_service import clear_permission_cache
    assert create_employee("till", "counterpass", "Counter", "User", "Salesman", actor_id=admin_emp_id)[0]
    clear_permission_cache()
    cert, key = ensure_shop_certificate(tmp_path / "tls", ["127.0.0.1"])
    service = ShopService()
    server = create_shop_server(("127.0.0.1", 0), str(cert), str(key), service=service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"https://127.0.0.1:{server.server_address[1]}"
    clients = []
    def connect(terminal="Counter-A", username="admin", password="secret123"):
        client = LanClient(url, str(cert), terminal, timeout=3)
        assert client.login(username, password)
        clients.append(client)
        return client
    yield {"connect": connect, "service": service, "db": seeded_shop,
           "admin": admin_emp_id, "url": url, "cert": cert, "tmp": tmp_path}
    for client in clients:
        client.logout()
    server.shutdown()
    server.server_close()
    thread.join(5)


def _sale(actor, token, *, qty=1):
    return {"customer_id": "WALKIN", "employee_id": actor,
            "cart": [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": qty}],
            "payment_method": "Credit Card", "checkout_token": token}


def test_authenticated_tls_read_sale_and_retry(lan_shop):
    client = lan_shop["connect"]()
    assert client.public_status()["configured"]
    assert client.call("InventoryModel", "search_products", "TestMed")
    request = _sale(lan_shop["admin"], "lan-first-sale")
    first = client.call("POSModel", "process_checkout", request, request_id="transport-first-sale")
    second = client.call("POSModel", "process_checkout", request, request_id="transport-first-sale")
    assert first["success"], first
    assert second["purchase_id"] == first["purchase_id"]
    with lan_shop["db"].get_db() as (_conn, cur):
        cur.execute("SELECT COUNT(*),MAX(terminal_id) FROM Purchase")
        assert cur.fetchone() == (1, "Counter-A")
        cur.execute("SELECT stock_quantity FROM Products WHERE id=1")
        assert cur.fetchone()[0] == 99


def test_two_counters_cannot_both_sell_the_last_unit(lan_shop):
    with lan_shop["db"].get_db(immediate=True) as (_conn, cur):
        cur.execute("UPDATE Products SET stock_quantity=1 WHERE id=1")
        cur.execute("UPDATE Batch SET quantity=1 WHERE id=1")
    first, second = lan_shop["connect"]("Counter-A"), lan_shop["connect"]("Counter-B")
    def submit(pair):
        client, token = pair
        return client.call("POSModel", "process_checkout", _sale(lan_shop["admin"], token), request_id=token)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [(first, "last-unit-a"), (second, "last-unit-b")]))
    assert sum(bool(row["success"]) for row in results) == 1, results
    with lan_shop["db"].get_db() as (_conn, cur):
        cur.execute("SELECT stock_quantity FROM Products WHERE id=1")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM Purchase")
        assert cur.fetchone()[0] == 1


def test_auth_actor_permissions_and_explicit_allowlist(lan_shop):
    client = lan_shop["connect"]("Counter-B", "till", "counterpass")
    assert LanClient(lan_shop["url"], str(lan_shop["cert"]), "Counter-C").login("till", "wrong") is None
    with pytest.raises(ShopAuthorizationError):
        client.call("SettingsModel", "set", "tax_rate", "0")
    with pytest.raises(ShopAuthorizationError):
        client.call("POSModel", "process_checkout", _sale(lan_shop["admin"], "forged-actor"))
    with pytest.raises(ShopOperationError):
        client.call("AuthModel", "__getattribute__", "password")
    client.logout()
    with pytest.raises(ShopAuthorizationError):
        client.call("InventoryModel", "search_products", "TestMed")


def test_response_lost_after_commit_does_not_repeat_sale(lan_shop, monkeypatch):
    client = lan_shop["connect"]()
    real_post = client._post
    dropped = []
    def drop_first_response(path, payload, **kwargs):
        result = real_post(path, payload, **kwargs)
        if path == "/v1/call" and not dropped:
            dropped.append(True)
            raise ShopConnectionError("simulated response loss")
        return result
    monkeypatch.setattr(client, "_post", drop_first_response)
    result = client.call("POSModel", "process_checkout", _sale(lan_shop["admin"], "lost-response"))
    assert result["success"]
    with lan_shop["db"].get_db() as (_conn, cur):
        cur.execute("SELECT COUNT(*) FROM Purchase")
        assert cur.fetchone()[0] == 1


def test_changed_request_identity_is_rejected(lan_shop):
    client = lan_shop["connect"]()
    request = _sale(lan_shop["admin"], "stable-checkout")
    assert client.call("POSModel", "process_checkout", request, request_id="same-transport")["success"]
    request["cart"][0]["qty"] = 2
    with pytest.raises(ShopOperationError):
        client.call("POSModel", "process_checkout", request, request_id="same-transport")


def test_wrong_certificate_is_never_trusted(lan_shop):
    other_cert, _key = ensure_shop_certificate(lan_shop["tmp"] / "other-shop", ["127.0.0.1"])
    client = LanClient(lan_shop["url"], str(other_cert), "Counter-C", timeout=2)
    with pytest.raises(ShopConnectionError):
        client.public_status()


def test_password_reset_revokes_existing_lan_session(lan_shop):
    from core.auth_service import update_employee_password
    client = lan_shop["connect"]()
    assert update_employee_password(lan_shop["admin"], "newsecret123", actor_id=lan_shop["admin"])[0]
    with pytest.raises(ShopAuthorizationError):
        client.call("InventoryModel", "search_products", "TestMed")


def test_server_restart_recovers_committed_pos_without_transport_response(lan_shop):
    client = lan_shop["connect"]()
    request = _sale(lan_shop["admin"], "crash-window-sale")
    result = client.call("POSModel", "process_checkout", request, request_id="crash-window-call")
    assert result["success"]
    with lan_shop["db"].get_db(immediate=True) as (_conn, cur):
        cur.execute("UPDATE Shop_Request SET response_json=NULL WHERE request_id='crash-window-call'")
    restarted = ShopService()
    recovered = restarted.call(client._token, "POSModel", "process_checkout", [request], {}, "crash-window-call")
    assert recovered["purchase_id"] == result["purchase_id"]
    assert recovered["duplicate"]
    with lan_shop["db"].get_db() as (_conn, cur):
        cur.execute("SELECT COUNT(*) FROM Purchase")
        assert cur.fetchone()[0] == 1


def test_unknown_non_pos_operation_never_repeats_blindly(lan_shop):
    client = lan_shop["connect"]()
    result = client.call("CustomerModel", "create", "Ayesha Account", request_id="create-customer")
    assert result[0]
    with lan_shop["db"].get_db(immediate=True) as (_conn, cur):
        cur.execute("UPDATE Shop_Request SET response_json=NULL WHERE request_id='create-customer'")
    with pytest.raises(ShopOperationError, match="uncertain outcome"):
        client.call("CustomerModel", "create", "Ayesha Account", request_id="create-customer")
    with lan_shop["db"].get_db() as (_conn, cur):
        cur.execute("SELECT COUNT(*) FROM Customers WHERE display_name='Ayesha Account'")
        assert cur.fetchone()[0] == 1


def test_existing_desktop_facades_use_shop_without_remote_recursion(lan_shop, monkeypatch):
    from core import lan_config
    from models import AppModel, AuthModel, InventoryModel, POSModel
    monkeypatch.setenv("PHARMA_KHAATO_SERVER_URL", lan_shop["url"])
    monkeypatch.setenv("PHARMA_KHAATO_SERVER_CERT", str(lan_shop["cert"]))
    monkeypatch.setenv("PHARMA_KHAATO_TERMINAL_ID", "Counter-UI")
    monkeypatch.setattr(lan_config, "_client", None)
    monkeypatch.setattr(lan_config, "_client_config", None)
    app = AppModel()
    app.initialize_database()
    assert app.has_registered_employees()
    user = AuthModel().login("admin", "secret123")
    assert user[0] == lan_shop["admin"]
    assert InventoryModel().search_products("TestMed")
    model = POSModel()
    request = model.checkout_request(**_sale(user[0], "existing-ui-facade"))
    result = model.process_checkout(request)
    assert result.success, result.message
    assert model.lookup_checkout_result(request.checkout_token, user[0]).purchase_id == result.purchase_id
    app.shutdown()


def test_supplier_invoice_and_cash_history_are_counter_bound(lan_shop):
    a, b = lan_shop['connect']('Counter-A'), lan_shop['connect']('Counter-B')
    actor = lan_shop['admin']
    opened = a.call('CashSessionModel', 'open_session', actor, 100, operation_id='lan-open-supplier')
    assert opened[0]
    received = a.call('InventoryModel', 'receive_invoice', 1, 'LAN-INVOICE', [
        {'product_id':1,'quantity':2,'unit_code':'base','cost_per_unit':10,
         'expiry':'12/2099','lot':'LAN-LOT','sale_price':15}], actor,
        operation_id='lan-supplier-receive', paid_amount=10, payment_method='Cash from drawer')
    assert received[0], received
    assert a.call('CashSessionModel', 'recent_movements')
    assert b.call('CashSessionModel', 'recent_movements') == []
    due = a.call('InventoryModel', 'supplier_accounts')[0]['balance']
    assert due == 10
    replay = a.call('InventoryModel', 'receive_invoice', 1, 'LAN-INVOICE', [
        {'product_id':1,'quantity':2,'unit_code':'base','cost_per_unit':10,
         'expiry':'12/2099','lot':'LAN-LOT','sale_price':15}], actor,
        operation_id='lan-supplier-receive', paid_amount=10, payment_method='Cash from drawer')
    assert replay[2]['invoice_id'] == received[2]['invoice_id']


def test_cashier_can_distinguish_missing_stock_and_read_only_own_close(lan_shop):
    client = lan_shop['connect']('Counter-Review', 'till', 'counterpass')
    assert client.call('POSModel', 'catalog_matches', 'TestMed') is True
    assert client.call('POSModel', 'catalog_matches', 'MissingMedicine') is False
    with pytest.raises(ShopAuthorizationError):
        client.call('CashSessionModel', 'last_closed_session', lan_shop['admin'])
    # The host supplies the authenticated employee and counter for this read.
    assert client.call('CashSessionModel', 'last_closed_session') is None
