"""Exact integer monetary storage and legacy API conversion boundary.

Ledger totals use paisa (100 per rupee). Catalog/cost prices retain four
places; historical per-base-unit division retains eight places. Existing
major-unit columns are normalized compatibility projections. Integer
companions are the authoritative values for aggregation/reconciliation.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# table -> column: integer scale. All identifiers are bundled constants.
MONEY_COLUMNS = {
    'Products': {'price': 10000},
    'Batch': {'cost_price': 10000, 'sale_price': 10000, 'mrp': 10000},
    'Purchase': {c: 100 for c in ('total_price','price_with_tax','discount_amount','cash_received','change_due','total_tax')},
    'Sales_details': {'unit_price': 100000000, 'line_subtotal': 100},
    'Customer_Khatoo': {'amount_paid': 100, 'amount_due': 100},
    'Cash_Register_Session': {c: 100 for c in ('opening_cash','closing_cash_actual','expected_cash_system','cash_discrepancy')},
    'Cash_Movement': {'amount': 100},
    'Customer_Returns': {'refund_amount': 100},
    'Return_Items': {'unit_price': 100000000, 'subtotal': 100000000},
    'Credit_Payment': {'amount': 100},
    'Refund_Transaction': {'amount': 100},
    'Credit_Payment_Operation': {'amount': 100, 'balance_after': 100},
    'Credit_Payment_Reversal': {'amount': 100},
}


def to_units(value, scale=100):
    if value is None:
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or abs(number) > Decimal('1000000000'):
            raise ValueError('Money must be finite and within the supported range.')
        units = int((number * int(scale)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        # Historical ledger fractions beyond a paisa need owner reconciliation,
        # not an implicit change of debt/refund entitlement. Tolerate only tiny
        # binary-float representation noise from the legacy compatibility API.
        if int(scale) == 100 and abs(number - Decimal(units) / 100) > Decimal('0.00000001'):
            raise ValueError('Sub-paisa ledger amount requires explicit historical reconciliation.')
        return units
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError('Invalid monetary amount.') from exc


def register(connection):
    connection.create_function('money_to_units', 2, to_units, deterministic=True)


def storage_reconciliation(connection):
    """Read-only report: never repair historical amounts implicitly."""
    issues = []
    counts = {}
    for table, columns in MONEY_COLUMNS.items():
        present = {r[1] for r in connection.execute(f'PRAGMA table_info("{table}")')}
        if not present:
            issues.append({'table': table, 'problem': 'missing_table'})
            continue
        for column, scale in columns.items():
            canonical = column + '_minor'
            if canonical not in present:
                issues.append({'table': table, 'column': column, 'problem': 'missing_integer_column'})
                if column in present:
                    for rowid, value in connection.execute(f'SELECT rowid,"{column}" FROM "{table}"'):
                        try:
                            to_units(value, scale)
                        except ValueError:
                            issues.append({'table':table,'rowid':rowid,'column':column,'problem':'legacy_amount_requires_review'})
                continue
            count = 0
            for rowid, value, integer in connection.execute(f'SELECT rowid,"{column}","{canonical}" FROM "{table}"'):
                count += 1
                try:
                    expected = to_units(value, scale)
                except ValueError:
                    expected = 'invalid'
                if expected != integer or (integer is not None and type(integer) is not int):
                    issues.append({'table':table,'rowid':rowid,'column':column,'problem':'integer_projection_mismatch'})
            counts[table] = count
    return {'ok': not issues, 'rows':counts, 'issues':issues}
