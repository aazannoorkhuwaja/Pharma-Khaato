"""Bounded, tokenized customer lookups, including Urdu names and local phones."""
from core.customer_service import escape_sql_like, normalize_search, normalize_phone, validate_cnic
from core.db_engine import get_db


def customer_filter(text='', alias='c'):
    raw = normalize_search(text)
    if not raw:
        return '1=1', []
    cnic = validate_cnic(raw)
    try:
        phone = normalize_phone(raw)
    except ValueError:
        phone = None
    if cnic or phone:
        value = cnic or phone
        return f'({alias}.id_card_number=%s OR {alias}.cnic=%s OR {alias}.phone=%s)', [value,value,value]
    fields = f"lower({alias}.display_name || ' ' || {alias}.first_name || ' ' || {alias}.last_name || ' ' || {alias}.city || ' ' || {alias}.phone)"
    terms = raw.split()[:8]
    return ' AND '.join(f"{fields} LIKE %s ESCAPE '\\'" for _ in terms), [f'%{escape_sql_like(t)}%' for t in terms]


def search_customers(text='', limit=60):
    if not str(text or '').strip():
        return []
    where, params = customer_filter(text)
    safe_limit = max(1,min(int(limit),120))
    with get_db() as (_conn,cur):
        cur.execute('SELECT c.id_card_number,c.first_name,c.last_name,c.phone,c.city '
                    f'FROM Customers c WHERE c.id_card_number != \'WALKIN\' AND ({where}) '
                    'ORDER BY c.display_name COLLATE NOCASE,c.id_card_number LIMIT %s', (*params,safe_limit))
        return cur.fetchall()


def search_customers_with_debt(text='', limit=120, offset=0):
    where,params = customer_filter(text)
    safe_limit = max(1,min(int(limit),250))
    with get_db() as (_conn,cur):
        cur.execute('SELECT c.id_card_number,c.first_name,c.last_name,c.phone,c.city, '
                    'COALESCE(SUM(k.amount_due),0) FROM Customers c '
                    'LEFT JOIN Customer_Khatoo k ON k.customer_id=c.id_card_number '
                    f'WHERE c.id_card_number != \'WALKIN\' AND ({where}) GROUP BY c.id_card_number '
                    'ORDER BY c.display_name COLLATE NOCASE,c.id_card_number LIMIT %s OFFSET %s',
                    (*params,safe_limit,max(0,int(offset))))
        return cur.fetchall()


def count_customers(text=''):
    where,params = customer_filter(text)
    with get_db() as (_conn,cur):
        cur.execute(f"SELECT COUNT(*) FROM Customers c WHERE c.id_card_number!='WALKIN' AND ({where})", params)
        return int(cur.fetchone()[0])
