"""One representation for money, used by every service.

Representation in the 2.4.x schema line:

* Monetary columns are SQLite ``REAL``. Every value is quantized to two decimal
  places *before* it is written, so the stored magnitude is exact for the
  amounts a pharmacy actually handles.
* ``SUM()`` over those columns is a float aggregate. The result therefore has
  to be quantized again at the boundary before it drives a decision, a printed
  total or a drawer count. Every report, ledger and receipt total does that
  through the helpers below.
* The supplier subsystem (migration ``025``) stores integer minor units
  (``total_minor``, ``amount_minor``, ``credit_minor``) and needs none of this.

Invariant: no money value reaches the database, a receipt, a report or a cash
count without passing through one of these helpers. ``tests/
test_money_and_audit_integrity.py`` guards the invariant, including a float
drift case.

Converting the legacy ``REAL`` columns to integer minor units is a destructive
schema change and is deliberately not done in place on a live shop database;
see ``docs/DATABASE.md`` for the staged plan.
"""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000")


def to_money(value) -> Decimal:
    """Quantize any stored or computed value to exact two-place money."""
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def to_money_float(value) -> float:
    """Quantize for display and report payloads that expect a float."""
    return float(to_money(value))


def checked_money(value, *, maximum=MAX_AMOUNT) -> Decimal:
    """Quantize an operator-supplied amount, rejecting invalid magnitudes."""
    amount = Decimal(str(value or 0))
    if not amount.is_finite() or abs(amount) > maximum:
        raise ValueError("Enter a valid finite amount.")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)
