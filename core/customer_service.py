import re
import time
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from core.db_engine import get_db, get_conn
from core.settings_service import SettingsService
from core.logger import get_logger

logger = get_logger("PharmaKhaatoCust")

# In-memory TTL Cache for Customer Searches
_CUST_CACHE: dict = {}
_CUST_CACHE_TTL = 5.0  # seconds

def _get_cust_cached(key):
    if key in _CUST_CACHE:
        val, timestamp = _CUST_CACHE[key]
        if time.time() - timestamp < _CUST_CACHE_TTL:
            return val
    return None

def _set_cust_cache(key, val):
    _CUST_CACHE[key] = (val, time.time())

def clear_customer_cache():
    global _CUST_CACHE
    _CUST_CACHE.clear()


def validate_cnic(cnic):
    """
    Validates and normalizes CNIC number string.
    Accepts 13 digits with or without dashes (e.g. 35202-1234567-1 or 3520212345671).
    Returns normalized 13-digit string or None if invalid.
    """
    if not cnic:
        return None
    cleaned = re.sub(r'[\s\-]', '', str(cnic).strip())
    if re.fullmatch(r'^\d{13}$', cleaned):
        return cleaned
    return None


def escape_sql_like(val):
    """Escapes % and _ wildcard characters for SQL LIKE pattern matching."""
    if not val:
        return ""
    return str(val).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def register_customer(cnic, fname, lname, email="N/A", city="N/A"):
    """Registers a customer with strict input validation."""
    valid_cnic = validate_cnic(cnic)
    if not valid_cnic:
        return False, "Invalid CNIC format. Must be 13 numeric digits (e.g., 3520212345671)."
    fname = str(fname).strip()[:50]
    lname = str(lname).strip()[:50]
    if not fname or not lname:
        return False, "First and Last names are required."
    email = email or "N/A"
    city = city or "N/A"

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id_card_number FROM Customers WHERE id_card_number = %s", (valid_cnic,)
            )
            if cur.fetchone():
                raise ValueError(f"Customer with CNIC {valid_cnic} is already registered.")
            cur.execute(
                "INSERT INTO Customers "
                "(id_card_number, first_name, last_name, Email_Address, city, registration_date) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (valid_cnic, fname, lname, email, city, date.today().strftime("%Y-%m-%d")),
            )
        clear_customer_cache()
        return True, f"Customer '{fname} {lname}' registered successfully!"
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Registration failed: {e}"


def search_customer(keyword):
    """
    Search customer by CNIC (exact match first, then partial) or First/Last Name with 5s TTL caching.
    Returns list of tuples: (id_card_number, first_name, last_name, email, city)
    """
    raw_kw = str(keyword).strip()
    if not raw_kw:
        return []

    cached = _get_cust_cached(raw_kw)
    if cached is not None:
        return cached

    try:
        with get_db() as (conn, cur):
            cleaned_cnic = validate_cnic(raw_kw)
            if cleaned_cnic:
                cur.execute(
                    "SELECT id_card_number, first_name, last_name, Email_Address, city "
                    "FROM Customers WHERE id_card_number = %s",
                    (cleaned_cnic,),
                )
                exact = cur.fetchall()
                if exact:
                    _set_cust_cache(raw_kw, exact)
                    return exact
            safe_kw = escape_sql_like(raw_kw)
            cur.execute(
                "SELECT id_card_number, first_name, last_name, Email_Address, city "
                "FROM Customers WHERE id_card_number LIKE %s OR first_name LIKE %s OR last_name LIKE %s",
                (f"%{safe_kw}%", f"%{safe_kw}%", f"%{safe_kw}%"),
            )
            res = cur.fetchall()
            _set_cust_cache(raw_kw, res)
            return res
    except Exception as e:
        logger.error(f"Customer search error: {e}")
        return []


def search_customers_with_debt(keyword=""):
    """
    Batched query returning customer tuples with total outstanding debt in a single SQL roundtrip:
    (id_card_number, first_name, last_name, email, city, total_debt)
    Eliminates N+1 debt queries on customer directory listing.
    """
    try:
        with get_db() as (conn, cur):
            raw_kw = str(keyword).strip()
            safe_kw = escape_sql_like(raw_kw)
            cur.execute(
                "SELECT c.id_card_number, c.first_name, c.last_name, c.Email_Address, c.city, "
                "       COALESCE(SUM(k.amount_due), 0.0) AS total_debt "
                "FROM Customers c "
                "LEFT JOIN Customer_Khatoo k ON k.customer_id = c.id_card_number "
                "WHERE c.id_card_number LIKE %s OR c.first_name LIKE %s OR c.last_name LIKE %s "
                "GROUP BY c.id_card_number, c.first_name, c.last_name, c.Email_Address, c.city "
                "ORDER BY c.first_name ASC",
                (f"%{safe_kw}%", f"%{safe_kw}%", f"%{safe_kw}%"),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Search customers with debt error: {e}")
        return []


def get_customer_total_debt(cnic, conn=None):
    """
    Returns total outstanding credit debt for a customer CNIC.
    Accepts an optional external connection to participate in a caller's transaction.
    """
    valid_cnic = validate_cnic(cnic)
    if not valid_cnic:
        return Decimal("0.00")

    # Opt-in conn path: caller owns the connection lifecycle
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT SUM(amount_due) FROM Customer_Khatoo WHERE customer_id = %s", (valid_cnic,)
            )
            res = cur.fetchone()
            if res and res[0] is not None:
                return Decimal(str(res[0])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return Decimal("0.00")
        except Exception as e:
            logger.error(f"Get customer total debt error: {e}")
            return Decimal("0.00")

    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT SUM(amount_due) FROM Customer_Khatoo WHERE customer_id = %s", (valid_cnic,)
            )
            res = cur.fetchone()
            if res and res[0] is not None:
                return Decimal(str(res[0])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return Decimal("0.00")
    except Exception as e:
        logger.error(f"Get customer total debt error: {e}")
        return Decimal("0.00")


def check_customer_credit_limit(cnic, new_credit_amount=0.0, conn=None):
    """
    Validates whether adding new_credit_amount would exceed customer's maximum credit limit.
    Returns (True, ok_msg) or (False, limit_exceeded_msg).
    Accepts an optional external connection to participate in a caller's transaction.
    """
    valid_cnic = validate_cnic(cnic)
    if not valid_cnic:
        return False, "Invalid Customer CNIC."
    current_debt = get_customer_total_debt(valid_cnic, conn=conn)
    try:
        add_dec = Decimal(str(new_credit_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError):
        return False, "Invalid credit amount."
    projected_debt = current_debt + add_dec
    limit_setting = SettingsService.get_setting("max_customer_credit_limit", "25000.00")
    max_limit = Decimal(str(limit_setting))
    if projected_debt > max_limit:
        return False, (
            f"Credit Limit Exceeded! Current Debt: Rs.{current_debt:.2f}, "
            f"Requested: Rs.{add_dec:.2f}, Projected Total: Rs.{projected_debt:.2f} "
            f"(Max Credit Limit: Rs.{max_limit:.2f})"
        )
    return True, "Credit limit approved."


def get_customer_debt_aging(cnic):
    """
    Calculates debt aging buckets (0-30 days, 31-60 days, 61+ days) for customer CNIC.
    """
    valid_cnic = validate_cnic(cnic)
    if not valid_cnic:
        return {"0_30": 0.0, "31_60": 0.0, "61_plus": 0.0}
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT k.amount_due, r.printing_date "
                "FROM Customer_Khatoo k "
                "JOIN Receipt r ON k.purchase_id = r.purchase_id "
                "WHERE k.customer_id = %s AND k.amount_due > 0",
                (valid_cnic,),
            )
            rows = cur.fetchall()

        today = date.today()
        bucket_30 = Decimal("0.00")
        bucket_60 = Decimal("0.00")
        bucket_plus = Decimal("0.00")
        for due, pdate_str in rows:
            due_dec = Decimal(str(due))
            try:
                pdate = datetime.strptime(str(pdate_str)[:10], "%Y-%m-%d").date()
                days_old = (today - pdate).days
            except Exception:
                days_old = 0
            if days_old <= 30:
                bucket_30 += due_dec
            elif days_old <= 60:
                bucket_60 += due_dec
            else:
                bucket_plus += due_dec
        return {
            "0_30": float(bucket_30),
            "31_60": float(bucket_60),
            "61_plus": float(bucket_plus),
        }
    except Exception as e:
        logger.error(f"Debt aging calculation error: {e}")
        return {"0_30": 0.0, "31_60": 0.0, "61_plus": 0.0}


def load_khatoo(keyword=""):
    """
    Returns Khatoo credit ledger records with safe query parameters.
    Tuples: (khatoo_id, customer_name, purchase_id, amount_due, amount_paid, customer_cnic)
    """
    try:
        with get_db() as (conn, cur):
            raw_kw = str(keyword).strip()
            safe_kw = escape_sql_like(raw_kw)
            if safe_kw:
                cur.execute(
                    "SELECT k.id, c.first_name || ' ' || c.last_name, k.purchase_id, "
                    "k.amount_due, k.amount_paid, k.customer_id "
                    "FROM Customer_Khatoo k "
                    "JOIN Customers c ON k.customer_id = c.id_card_number "
                    "WHERE c.id_card_number = %s OR c.first_name LIKE %s OR c.last_name LIKE %s",
                    (raw_kw, f"%{safe_kw}%", f"%{safe_kw}%"),
                )
            else:
                cur.execute(
                    "SELECT k.id, c.first_name || ' ' || c.last_name, k.purchase_id, "
                    "k.amount_due, k.amount_paid, k.customer_id "
                    "FROM Customer_Khatoo k "
                    "JOIN Customers c ON k.customer_id = c.id_card_number "
                    "ORDER BY k.id DESC"
                )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Load Khatoo error: {e}")
        return []


def record_payment(khatoo_id, amount):
    """Updates amount_paid and amount_due for a Khatoo entry with Decimal input validation."""
    try:
        dec_amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if dec_amount <= Decimal("0.00"):
            return False, "Payment amount must be greater than zero."
    except (ValueError, TypeError):
        return False, "Invalid payment amount specified."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT amount_due, amount_paid FROM Customer_Khatoo WHERE id = %s", (khatoo_id,)
            )
            res = cur.fetchone()
            if not res:
                raise ValueError("Khatoo record not found.")
            due_dec = Decimal(str(res[0])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            paid_dec = Decimal(str(res[1])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if dec_amount > due_dec:
                raise ValueError(
                    f"Payment amount (Rs.{dec_amount:.2f}) exceeds "
                    f"outstanding due balance (Rs.{due_dec:.2f})."
                )
            cur.execute(
                "UPDATE Customer_Khatoo SET amount_paid = %s, amount_due = %s WHERE id = %s",
                (float(paid_dec + dec_amount), float(due_dec - dec_amount), khatoo_id),
            )
        return True, "Payment recorded successfully."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Payment recording failed: {e}"


def get_khatoo_summary():
    """Returns sum of total pending debt across all customers."""
    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT SUM(amount_due) FROM Customer_Khatoo")
            res = cur.fetchone()
            return float(res[0]) if res and res[0] is not None else 0.0
    except Exception as e:
        logger.error(f"Get Khatoo summary error: {e}")
        return 0.0
