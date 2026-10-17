"""Customer identities and balances without requiring national identity details."""
import re
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.db_engine import get_db
from core.settings_service import SettingsService
from core.logger import get_logger

logger = get_logger('PharmaKhaatoCust')


def normalize_digits(value):
    return ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c
                   for c in unicodedata.normalize('NFKC', str(value or '')))


def normalize_search(value):
    return ' '.join(normalize_digits(value).casefold().split())


def validate_cnic(cnic):
    cleaned = re.sub(r'[\s\-]', '', normalize_digits(cnic))
    return cleaned if re.fullmatch(r'[0-9]{13}', cleaned) else None


def normalize_phone(phone):
    if not str(phone or '').strip():
        return ''
    cleaned = re.sub(r'[\s()+.\-]', '', normalize_digits(phone))
    if cleaned.startswith('0092'):
        cleaned = '0' + cleaned[4:]
    elif cleaned.startswith('92') and len(cleaned) == 12:
        cleaned = '0' + cleaned[2:]
    if not re.fullmatch(r'0[0-9]{9,10}', cleaned):
        raise ValueError('Enter a local phone number, such as 0300 1234567, or leave it blank.')
    return cleaned


def escape_sql_like(value):
    return str(value or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def clear_customer_cache():
    """Compatibility hook: customer reads now use fresh bounded queries."""


@contextmanager
def _cursor(conn=None):
    if conn is not None:
        yield conn.cursor()
    else:
        with get_db() as (_conn, cur):
            yield cur


def resolve_customer_ref(customer_ref, conn=None):
    """Resolve an opaque selected reference, or a normalized CNIC, without guessing."""
    raw = str(customer_ref or '').strip()
    if not raw or raw.upper() == 'WALKIN':
        raise ValueError('Select a customer account first.')
    with _cursor(conn) as cur:
        cur.execute('SELECT id_card_number FROM Customers WHERE id_card_number = %s', (raw,))
        row = cur.fetchone()
        if row:
            return str(row[0])
        cnic = validate_cnic(raw)
        if cnic:
            cur.execute('SELECT id_card_number FROM Customers WHERE cnic = %s OR id_card_number = %s',
                        (cnic, cnic))
            rows = cur.fetchall()
            if len(rows) == 1:
                return str(rows[0][0])
            if len(rows) > 1:
                raise ValueError('More than one account has these identity details. Select the customer by name and area.')
    raise ValueError('This customer account could not be found.')


def create_customer(display_name, phone='', area='', cnic='', employee_id=None, *, last_name='', email='N/A'):
    """Create a name-only account; contact and CNIC are optional, never generated."""
    name = ' '.join(str(display_name or '').strip().split())
    last = ' '.join(str(last_name or '').strip().split())
    if not name or len(name) > 100 or len(last) > 100:
        return False, 'Enter the customer name (up to 100 characters).', None
    full_name = ' '.join(part for part in (name, last) if part)
    try:
        phone = normalize_phone(phone)
        normalized_cnic = validate_cnic(cnic)
        if str(cnic or '').strip() and not normalized_cnic:
            raise ValueError('CNIC must contain 13 digits, or leave it blank.')
        if employee_id is not None:
            from core.permission_service import require_permission
            allowed, reason = require_permission(employee_id, 'customer.create')
            if not allowed:
                return False, reason, None
        ref = normalized_cnic or ('CUST_' + uuid.uuid4().hex)
        with get_db(immediate=True) as (_conn, cur):
            if normalized_cnic:
                # Also catch legacy identities stored using Urdu/Persian digits.
                cur.execute('SELECT id_card_number, cnic FROM Customers WHERE id_card_number != %s', ('WALKIN',))
                if any(validate_cnic(existing_cnic or existing_ref) == normalized_cnic
                       for existing_ref, existing_cnic in cur.fetchall()):
                    raise ValueError('A customer already uses this CNIC. Find their existing account instead.')
            cur.execute(
                'INSERT INTO Customers (id_card_number,first_name,last_name,Email_Address,city,registration_date,display_name,phone,cnic) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (ref,name,last,str(email or 'N/A').strip()[:150],str(area or '').strip()[:100],
                 date.today().isoformat(),full_name,phone,normalized_cnic))
        return True, f'Customer {full_name} added.', ref
    except ValueError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception('Customer creation failed')
        return False, 'The customer could not be saved. Try again.', None


def register_customer(cnic, fname, lname='', email='N/A', city='N/A', *, phone=''):
    ok, message, _ref = create_customer(fname, phone, city, cnic, last_name=lname, email=email)
    return ok, message


def search_customer(keyword):
    from core.customer_directory_service import search_customers
    return search_customers(keyword)


def search_customers_with_debt(keyword=''):
    from core.customer_directory_service import search_customers_with_debt as search
    return search(keyword)


def get_customer_total_debt(customer_ref, conn=None):
    """A failed balance read raises; unavailable credit must never look like zero."""
    with _cursor(conn) as cur:
        ref = resolve_customer_ref(customer_ref, conn)
        cur.execute('SELECT COALESCE(SUM(amount_due),0) FROM Customer_Khatoo WHERE customer_id=%s', (ref,))
        return Decimal(str(cur.fetchone()[0])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def check_customer_credit_limit(customer_ref, new_credit_amount=0.0, conn=None):
    try:
        amount = Decimal(str(new_credit_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        limit = Decimal(str(SettingsService.get_setting('max_customer_credit_limit', '25000.00')))
        if not amount.is_finite() or amount < 0 or not limit.is_finite() or limit < 0:
            raise ValueError('Invalid credit amount or limit.')
        debt = get_customer_total_debt(customer_ref, conn)
        if debt + amount > limit:
            return False, f'Credit limit reached. Due Rs. {debt:.2f}; this sale Rs. {amount:.2f}; limit Rs. {limit:.2f}.'
        return True, 'Credit limit approved.'
    except (ValueError, TypeError, InvalidOperation) as exc:
        return False, str(exc)
    except Exception:
        logger.exception('Credit balance verification failed')
        return False, 'The customer balance could not be verified. Try again before issuing credit.'


def get_customer_debt_aging(customer_ref):
    ref = resolve_customer_ref(customer_ref)
    with get_db() as (_conn, cur):
        cur.execute('SELECT k.amount_due,r.printing_date FROM Customer_Khatoo k '
                    'JOIN Receipt r ON r.purchase_id=k.purchase_id WHERE k.customer_id=%s AND k.amount_due>0', (ref,))
        rows = cur.fetchall()
    buckets = {'0_30': Decimal('0'), '31_60': Decimal('0'), '61_plus': Decimal('0')}
    for due, sale_date in rows:
        age = (date.today()-date.fromisoformat(str(sale_date)[:10])).days
        buckets['0_30' if age <= 30 else '31_60' if age <= 60 else '61_plus'] += Decimal(str(due))
    return {key: float(value) for key,value in buckets.items()}


def load_khatoo(keyword=''):
    from core.credit_query_service import load_open_credit
    return load_open_credit(keyword)


def record_payment(khatoo_id, amount):
    return False, 'Sign in and use Record Payment so the payment has a staff and tender history.'


def get_khatoo_summary():
    from core.credit_query_service import total_open_credit
    return total_open_credit()
