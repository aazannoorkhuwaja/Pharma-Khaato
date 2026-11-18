"""The shared financial audit trail must use the configured shop clock."""
from datetime import datetime


def test_audit_timestamp_uses_business_clock(fresh_db, monkeypatch):
    from core import audit_service
    monkeypatch.setattr(audit_service, 'business_now', lambda: datetime(2001, 2, 3, 4, 5, 6))
    assert audit_service.log_audit_event('1', 'CLOCK_REGRESSION', 'test')
    with fresh_db.get_db() as (_, cur):
        cur.execute('SELECT timestamp FROM Audit_Log WHERE action=%s', ('CLOCK_REGRESSION',))
        assert cur.fetchone()[0] == '2001-02-03 04:05:06'
