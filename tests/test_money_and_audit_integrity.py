"""Money representation and audit-clock contracts.

Both checks protect a real pharmacy failure mode: a total that drifts by a
cent, and an audit trail that cannot be ordered against the cash shift it
belongs to because two different clocks wrote into one table.
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from core.business_time import business_now
from core.money import CENT, checked_money, to_money, to_money_float


def test_quantization_is_half_up_at_two_places():
    assert to_money("0.005") == Decimal("0.01")
    assert to_money("1.004") == Decimal("1.00")
    assert to_money(None) == Decimal("0.00")
    assert CENT == Decimal("0.01")


def test_float_aggregate_drift_collapses_back_to_the_exact_total():
    """A float aggregate must never leak into a printed or reconciled total."""
    assert 0.1 + 0.2 != 0.3, "the drift case this guard exists for has disappeared"
    assert to_money(0.1 + 0.2) == Decimal("0.30")

    # 3000 counter lines of Rs.0.07, as SQL SUM() returns it over REAL columns.
    naive = sum([0.07] * 3000)
    exact = sum((to_money(0.07) for _ in range(3000)), Decimal("0.00"))
    assert exact == Decimal("210.00")
    assert to_money_float(naive) == 210.0


def test_checked_money_rejects_invalid_amounts():
    for invalid in ("nan", "inf", "-inf", 10**12):
        with pytest.raises(ValueError):
            checked_money(invalid)


def test_every_service_uses_the_same_quantum():
    """Six duplicated helpers must not be able to disagree about a cent."""
    from core import (
        cash_session_service,
        credit_payment_service,
        receipt_service,
        reports_service,
        return_service,
    )

    for value in ("0.005", "12.345", "-0.005", 0, None):
        expected = to_money(value)
        assert cash_session_service._money(value) == expected
        assert receipt_service._money(value) == expected
        assert return_service._money(value) == expected
        assert reports_service._money(value) == float(expected)
    # credit_payment keeps its own validation message but shares the quantum.
    assert credit_payment_service._money("0.005") == Decimal("0.01")


def test_audit_events_are_stamped_in_shop_time(fresh_db, monkeypatch):
    """A workstation clock must not be able to misdate the audit trail."""
    monkeypatch.setenv("PHARMA_KHAATO_TIMEZONE", "Asia/Karachi")
    monkeypatch.setenv("TZ", "UTC")
    if hasattr(time, "tzset"):  # POSIX only; Windows CI keeps its own zone
        time.tzset()

    from core import audit_service

    before = business_now().replace(tzinfo=None, microsecond=0)
    assert audit_service.log_audit_event("1", "SHIFT_NOTE", "closed") is True
    after = business_now().replace(tzinfo=None, microsecond=0)

    rows = audit_service.get_audit_logs(limit=1)
    assert rows, "the audit event was not persisted"
    stamp = datetime.strptime(rows[0][1], "%Y-%m-%d %H:%M:%S")
    assert before <= stamp <= after + timedelta(seconds=1)
