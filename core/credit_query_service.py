"""Credit balances with explicit paging and errors that remain visible."""
from core.customer_directory_service import customer_filter
from core.db_engine import get_db


def load_open_credit(text='',limit=200,offset=0):
    where,params=customer_filter(text)
    with get_db() as (_conn,cur):
        cur.execute("SELECT k.id,c.display_name,k.purchase_id,k.amount_due,k.amount_paid,k.customer_id "
                    "FROM Customer_Khatoo k JOIN Customers c ON c.id_card_number=k.customer_id "
                    f"WHERE k.amount_due>0 AND ({where}) ORDER BY k.id ASC LIMIT %s OFFSET %s",
                    (*params,max(1,min(int(limit),500)),max(0,int(offset))))
        return cur.fetchall()


def load_credit_accounts(text='',limit=100,offset=0):
    where,params=customer_filter(text)
    with get_db() as (_conn,cur):
        cur.execute('SELECT c.id_card_number,c.display_name,c.phone,c.city,SUM(k.amount_due),COUNT(*) '
                    'FROM Customers c JOIN Customer_Khatoo k ON k.customer_id=c.id_card_number '
                    f'WHERE k.amount_due>0 AND ({where}) GROUP BY c.id_card_number '
                    'ORDER BY MIN(k.id) ASC LIMIT %s OFFSET %s',
                    (*params,max(1,min(int(limit),500)),max(0,int(offset))))
        return cur.fetchall()


def count_credit_accounts(text=''):
    where,params=customer_filter(text)
    with get_db() as (_conn,cur):
        cur.execute('SELECT COUNT(DISTINCT c.id_card_number) FROM Customers c '
                    'JOIN Customer_Khatoo k ON k.customer_id=c.id_card_number '
                    f'WHERE k.amount_due>0 AND ({where})', params)
        return int(cur.fetchone()[0])


def total_open_credit():
    with get_db() as (_conn,cur):
        cur.execute('SELECT COALESCE(SUM(amount_due),0) FROM Customer_Khatoo WHERE amount_due>0')
        return float(cur.fetchone()[0])
