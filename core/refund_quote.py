"""Shared cumulative-cent allocation for refund previews and transactions."""
from decimal import Decimal, ROUND_HALF_UP


def quote_refund(gross, base, returned_base, requested_base, already_refunded, final=False):
    gross, base, returned_base, requested_base, already_refunded = map(
        lambda value: Decimal(str(value)), (gross, base, returned_base, requested_base, already_refunded))
    remaining = max(gross - already_refunded, Decimal('0'))
    if final:
        return remaining
    if base <= 0:
        return Decimal('0')
    cumulative = (gross * (returned_base + requested_base) / base).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return max(Decimal('0'), min(remaining, cumulative - already_refunded))
