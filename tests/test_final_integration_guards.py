"""Cross-session and disconnected-counter safeguards from final integration."""
import pytest


def test_stale_model_hold_cannot_attach_to_new_sale(seeded_shop, admin_emp_id):
    from models.services import LOCAL_MODELS
    from core.hold_sale_service import hold_sale
    from core.pos_service import CheckoutRequest
    cart = [{'prod_id': 1, 'name': 'TestMed', 'price': 15, 'qty': 1, 'subtotal': 15}]
    ok, held = hold_sale('WALKIN', admin_emp_id, cart)
    assert ok
    model = LOCAL_MODELS['POSModel']()
    assert model.recall_sale(held, admin_emp_id)[0]
    # Another draft/session reuses the model but has no association with that hold.
    request = CheckoutRequest('WALKIN', admin_emp_id, cart, payment_method='Credit Card', checkout_token='unrelated-new-bill')
    result = model.process_checkout(request)
    assert result.success, result.message
    assert request.held_sale_id is None
    with seeded_shop.get_db() as (_conn, cur):
        cur.execute('SELECT status FROM Hold_Sales WHERE id=%s', (held,))
        assert cur.fetchone()[0] == 'RESUMED'
    ok, new_held = model.hold_sale('WALKIN', admin_emp_id, cart, draft={'cart':cart})
    assert ok and new_held != held


def test_settings_read_failure_does_not_return_plausible_defaults(monkeypatch):
    from core import settings_service
    def unavailable():
        raise OSError('database unavailable')
    monkeypatch.setattr(settings_service, 'get_db', unavailable)
    with pytest.raises(RuntimeError, match='could not be read'):
        settings_service.SettingsService.get_many(['default_tax_rate'])


def test_counter_backup_actions_do_not_open_local_database(monkeypatch):
    from controllers.settings_controller import SettingsController
    from core import lan_config, permission_service, backup_service
    monkeypatch.setattr(lan_config, 'load_counter_config', lambda: {'server_url':'https://shop:8765'})
    def unexpected(*args, **kwargs):
        raise AssertionError('Counter must not read a local business database')
    monkeypatch.setattr(permission_service, 'require_permission', unexpected)
    monkeypatch.setattr(backup_service, 'backup_destination', unexpected)
    controller = SettingsController(settings_model=object(), auth_model=object())
    assert 'main shop computer' in controller.backup_destination()
    assert not controller.configure_backup_destination('/tmp/not-used')[0]
    assert not controller.restore_backup('/tmp/not-used', 1)[0]
