"""Customer discounts, applied before sales tax. Monetary values are rupees."""
from decimal import Decimal, ROUND_HALF_UP


def discount_amounts(subtotal, government_percent, owner_percent):
    subtotal = Decimal(str(subtotal))
    rates = [Decimal(str(rate)) for rate in (government_percent, owner_percent)]
    if any(not rate.is_finite() or not 0 <= rate <= 100 for rate in rates):
        raise ValueError("Discount percentages must be between 0 and 100.")
    def amount(base, rate):
        return (base * rate / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    government = amount(subtotal, rates[0])
    return government, amount(subtotal - government, rates[1])
