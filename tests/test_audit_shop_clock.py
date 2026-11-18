"""The shared financial audit trail must use the configured shop clock."""
from datetime import datetime


def test_audit_timestamp_uses_business_clock(fresh_db, monkeypatch):
    from core import audit_service
    monkeypatch.setattr(audit_service, 'business_now', lambda: datetime(2001, 2, 3, 4, 5, 6))
    assert audit_service.log_audit_event('1', 'CLOCK_REGRESSION', 'test')
    with fresh_db.get_db() as (_, cur):
        cur.execute('SELECT timestamp FROM Audit_Log WHERE action=%s', ('CLOCK_REGRESSION',))
        assert cur.fetchone()[0] == '2001-02-03 04:05:06'


def test_invalid_clock_prevents_password_change(seeded_shop, monkeypatch):
    import pytest
    from core import auth_service
    from core.business_time import ShopClockError
    conn = seeded_shop.get_conn()
    original = conn.cursor().execute('SELECT password FROM Employee WHERE Employee_id=1').fetchone()[0]
    with monkeypatch.context() as clock:
        clock.setenv('PHARMA_KHAATO_TIMEZONE', 'Asia/Karaci')
        with pytest.raises(ShopClockError, match='PHARMA_KHAATO_TIMEZONE'):
            seeded_shop.get_conn()
        assert not auth_service.change_password(1, 'secret123', 'new-password-456')[0]
    assert conn.cursor().execute('SELECT password FROM Employee WHERE Employee_id=1').fetchone()[0] == original


def test_startup_rejects_invalid_clock_before_model_initialization(monkeypatch):
    import pytest
    from unittest.mock import Mock
    from controllers.application_controller import ApplicationController
    from core.business_time import ShopClockError
    model = Mock()
    monkeypatch.setenv('PHARMA_KHAATO_TIMEZONE', 'Asia/Karaci')
    with pytest.raises(ShopClockError):
        ApplicationController(model).initialize()
    model.initialize_database.assert_not_called()
