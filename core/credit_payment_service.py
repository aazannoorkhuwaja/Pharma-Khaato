"""Durable account repayments, printed statements and auditable corrections."""
from core.business_time import business_now
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import uuid

from core.db_engine import get_db
from core.money import CENT
from core.customer_service import resolve_customer_ref
from core.logger import get_logger
from core.permission_service import require_permission

logger = get_logger('PharmaKhaatoCreditPayments')
_ALLOWED_METHODS={'cash':'Cash','card':'Credit Card','credit card':'Credit Card',
                  'easypaisa':'Easypaisa','jazzcash':'JazzCash','bank transfer':'Bank Transfer','raast':'Raast'}


def _money(value):
    amount=Decimal(str(value)).quantize(CENT,rounding=ROUND_HALF_UP)
    if not amount.is_finite():
        raise ValueError('Enter a valid amount.')
    return amount


def _token(value):
    token=str(value or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',token):
        raise ValueError('A payment safety reference is required. Reopen the payment form.')
    return token


def _cash_session(cur,employee_id,terminal_id=None):
    cur.execute("SELECT id FROM Cash_Register_Session WHERE employee_id=%s AND status='OPEN' AND terminal_id=%s ORDER BY id DESC LIMIT 1",(employee_id,terminal_id or 'local'))
    row=cur.fetchone()
    if not row:
        raise ValueError('Start a cash shift before accepting or reversing a cash payment.')
    return int(row[0])


def _audit(cur,employee_id,action,details,now):
    cur.execute('INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES (%s,%s,%s,%s)',
                (now,str(employee_id),action,details))


def record_customer_payment(customer_ref,amount,employee_id,payment_method='Cash',note='',*,operation_id=None,ledger_id=None,terminal_id=None):
    """Apply one handover oldest-first; retrying its ID returns the same payment."""
    try:
        amount_dec=_money(amount)
        employee_id=int(employee_id)
        operation_id=_token(operation_id)
        ledger_id=int(ledger_id) if ledger_id is not None else None
        if amount_dec<=0:
            raise ValueError('Payment amount must be greater than zero.')
        method=_ALLOWED_METHODS.get(str(payment_method or 'Cash').strip().lower())
        if not method:
            raise ValueError('Choose a supported payment method.')
        note=str(note or '').strip()[:250]
    except (ValueError,TypeError,InvalidOperation) as exc:
        return False,str(exc),{'outcome':'not_recorded'}
    allowed,reason=require_permission(employee_id,'credit.collect')
    if not allowed:
        return False,reason,{'outcome':'not_recorded'}
    try:
        with get_db(immediate=True) as (conn,cur):
            ref=resolve_customer_ref(customer_ref,conn)
            cur.execute('SELECT customer_id,employee_id,amount,payment_method,note,ledger_id,balance_after '
                        'FROM Credit_Payment_Operation WHERE operation_id=%s',(operation_id,))
            previous=cur.fetchone()
            if previous:
                if (previous[0],int(previous[1]),_money(previous[2]),previous[3],previous[4],previous[5]) != (ref,employee_id,amount_dec,method,note,ledger_id):
                    return False,'This payment reference was already used for different details. Check payment history.',{'outcome':'conflict'}
                cur.execute('SELECT id FROM Credit_Payment WHERE operation_id=%s ORDER BY id',(operation_id,))
                ids=[int(row[0]) for row in cur.fetchall()]
                return True,'This payment was already recorded.',{'operation_id':operation_id,'payment_ids':ids,'customer_id':ref,'amount':float(amount_dec),'balance':float(previous[6]),'already_recorded':True}
            where='customer_id=%s AND amount_due>0'
            params=[ref]
            if ledger_id is not None:
                where+=' AND id=%s';params.append(ledger_id)
            cur.execute(f'SELECT id,amount_due,amount_paid FROM Customer_Khatoo WHERE {where} ORDER BY id ASC',params)
            ledgers=cur.fetchall()
            due=sum((_money(row[1]) for row in ledgers),Decimal('0'))
            if amount_dec>due:
                raise ValueError(f'Payment exceeds the remaining balance of Rs. {due:.2f}.')
            if not ledgers:
                raise ValueError('This customer has no unpaid balance.')
            session_id=_cash_session(cur,employee_id,terminal_id) if method=='Cash' else None
            now=business_now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('INSERT INTO Credit_Payment_Operation(operation_id,customer_id,employee_id,amount,payment_method,note,ledger_id,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                        (operation_id,ref,employee_id,float(amount_dec),method,note,ledger_id,now))
            remaining=amount_dec;ids=[]
            for khatoo_id,due_raw,paid_raw in ledgers:
                if remaining<=0:
                    break
                applied=min(remaining,_money(due_raw))
                cur.execute('UPDATE Customer_Khatoo SET amount_paid=%s,amount_due=%s WHERE id=%s',
                            (float(_money(paid_raw)+applied),float(_money(due_raw)-applied),khatoo_id))
                cur.execute('INSERT INTO Credit_Payment(khatoo_id,customer_id,employee_id,session_id,amount,payment_method,paid_at,note,operation_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                            (khatoo_id,ref,employee_id,session_id,float(applied),method,now,note,operation_id))
                ids.append(int(cur.lastrowid));remaining-=applied
            cur.execute('SELECT COALESCE(SUM(amount_due),0) FROM Customer_Khatoo WHERE customer_id=%s',(ref,))
            balance=_money(cur.fetchone()[0])
            cur.execute('UPDATE Credit_Payment_Operation SET balance_after=%s WHERE operation_id=%s',(float(balance),operation_id))
            _audit(cur,employee_id,'CUSTOMER_CREDIT_PAYMENT',f'Payment {operation_id}; {method}; Rs.{amount_dec:.2f}; {len(ids)} bill(s).',now)
        return True,f'Payment of Rs. {amount_dec:.2f} recorded. Remaining Rs. {balance:.2f}.',{'operation_id':operation_id,'payment_ids':ids,'customer_id':ref,'amount':float(amount_dec),'balance':float(balance),'already_recorded':False}
    except ValueError as exc:
        return False,str(exc),{'outcome':'not_recorded'}
    except Exception:
        logger.exception('Credit payment failed')
        return False,'The payment could not be confirmed. Retry using the same payment form.',None


def record_credit_payment(ledger_id,amount,employee_id,payment_method='Cash',note='',*,operation_id=None,terminal_id=None):
    """Compatibility API for a specific invoice, using the same locked writer."""
    try:
        with get_db() as (_conn,cur):
            cur.execute('SELECT customer_id FROM Customer_Khatoo WHERE id=%s',(int(ledger_id),))
            row=cur.fetchone()
        if not row:
            return False,'This customer-credit entry no longer exists.'
        ok,message,_details=record_customer_payment(row[0],amount,employee_id,payment_method,note,
                          operation_id=operation_id or uuid.uuid4().hex,ledger_id=ledger_id,terminal_id=terminal_id)
        return ok,message
    except (ValueError,TypeError):
        return False,'Invalid customer-credit entry.'
    except Exception:
        logger.exception('Credit payment lookup failed')
        return False,'The customer balance is unavailable. Try again.'


def reverse_credit_payment(payment_id,employee_id,reason,*,operation_id=None,terminal_id=None):
    """Owner/manager correction, with immutable original payment and audit trail."""
    try:
        payment_id=int(payment_id);employee_id=int(employee_id);operation_id=_token(operation_id)
        reason=str(reason or '').strip()
        if not reason or len(reason)>250:
            raise ValueError('Enter a short reason for correcting this payment.')
    except (ValueError,TypeError) as exc:
        return False,str(exc),None
    allowed,message=require_permission(employee_id,'credit.reverse')
    if not allowed:
        return False,'An owner or manager must sign in to reverse a payment.',None
    try:
        with get_db(immediate=True) as (_conn,cur):
            cur.execute('SELECT id,payment_id,employee_id,reason FROM Credit_Payment_Reversal WHERE operation_id=%s',(operation_id,))
            previous=cur.fetchone()
            if previous:
                if previous[1:]!=(payment_id,employee_id,reason):
                    raise ValueError('This correction reference was already used for other details.')
                return True,'This correction was already recorded.',{'reversal_id':previous[0]}
            cur.execute('SELECT cp.khatoo_id,cp.amount,cp.payment_method,cp.customer_id,k.amount_paid,k.amount_due '
                        'FROM Credit_Payment cp JOIN Customer_Khatoo k ON k.id=cp.khatoo_id WHERE cp.id=%s',(payment_id,))
            row=cur.fetchone()
            if not row:
                raise ValueError('The original payment could not be found.')
            khatoo_id,amount,method,ref,paid,due=row;amount=_money(amount)
            cur.execute('SELECT id FROM Credit_Payment_Reversal WHERE payment_id=%s',(payment_id,))
            if cur.fetchone():
                raise ValueError('This payment has already been reversed.')
            cur.execute('SELECT COALESCE(SUM(amount),0) FROM Refund_Transaction WHERE source_credit_payment_id=%s',(payment_id,))
            if _money(cur.fetchone()[0])>0:
                raise ValueError('This payment has already funded a return refund. Use the return history to reconcile it.')
            if _money(paid)<amount:
                raise ValueError('The paid balance no longer supports reversing this payment. Review the account history.')
            session_id=_cash_session(cur,employee_id,terminal_id) if method=='Cash' else None
            now=business_now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('INSERT INTO Credit_Payment_Reversal(payment_id,operation_id,employee_id,session_id,amount,payment_method,created_at,reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                        (payment_id,operation_id,employee_id,session_id,float(amount),method,now,reason))
            reversal_id=int(cur.lastrowid)
            cur.execute('UPDATE Customer_Khatoo SET amount_paid=%s,amount_due=%s WHERE id=%s',
                        (float(_money(paid)-amount),float(_money(due)+amount),khatoo_id))
            if method=='Cash':
                cur.execute("INSERT INTO Cash_Movement(session_id,employee_id,movement_type,amount,reason,created_at) VALUES (%s,%s,'CASH_OUT',%s,%s,%s)",
                            (session_id,employee_id,float(amount),f'Credit payment correction #{reversal_id}: {reason}',now))
            _audit(cur,employee_id,'CUSTOMER_CREDIT_PAYMENT_REVERSED',f'Payment #{payment_id}; correction #{reversal_id}; Rs.{amount:.2f}; {reason}',now)
        return True,f'Payment corrected. Rs. {amount:.2f} is due again.',{'reversal_id':reversal_id,'customer_id':ref,'amount':float(amount),'method':method}
    except ValueError as exc:
        return False,str(exc),None
    except Exception:
        logger.exception('Credit payment reversal failed')
        return False,'The correction could not be confirmed. Retry with the same correction reference.',None


def recent_credit_payments(limit=100,customer_ref=None,offset=0):
    params=[];where=''
    if customer_ref:
        where='WHERE cp.customer_id=%s';params.append(resolve_customer_ref(customer_ref))
    with get_db() as (_conn,cur):
        cur.execute('SELECT cp.id,cp.khatoo_id,cp.amount,cp.payment_method,cp.paid_at,e.username,cp.note, '
                    'c.display_name,cp.operation_id,COALESCE(rv.id,0),cp.customer_id FROM Credit_Payment cp '
                    'JOIN Employee e ON e.Employee_id=cp.employee_id JOIN Customers c ON c.id_card_number=cp.customer_id '
                    'LEFT JOIN Credit_Payment_Reversal rv ON rv.payment_id=cp.id '
                    f'{where} ORDER BY cp.id DESC LIMIT %s OFFSET %s',(*params,max(1,min(int(limit),500)),max(0,int(offset))))
        return cur.fetchall()


def count_credit_payments(customer_ref=None):
    with get_db() as (_conn,cur):
        if customer_ref:
            cur.execute('SELECT COUNT(*) FROM Credit_Payment WHERE customer_id=%s',(resolve_customer_ref(customer_ref),))
        else:
            cur.execute('SELECT COUNT(*) FROM Credit_Payment')
        return int(cur.fetchone()[0])


def payment_receipt_text(operation_id):
    with get_db() as (_conn,cur):
        cur.execute('SELECT o.operation_id,c.display_name,o.amount,o.payment_method,o.created_at,o.balance_after,e.username '
                    'FROM Credit_Payment_Operation o JOIN Customers c ON c.id_card_number=o.customer_id '
                    'JOIN Employee e ON e.Employee_id=o.employee_id WHERE o.operation_id=%s',(str(operation_id),))
        row=cur.fetchone()
        if not row:
            raise ValueError('This payment receipt is unavailable.')
    reference,name,amount,method,when,balance,staff=row
    return '\n'.join(['CUSTOMER PAYMENT RECEIPT','-'*32,f'Customer: {name}',f'Date: {when}',f'Paid: Rs. {_money(amount):.2f}',
                      f'Method: {method}',f'Remaining: Rs. {_money(balance):.2f}',f'Staff: {staff}',f'Ref: {reference}',
                      '-'*32,'Keep this slip for your records.'])


def customer_statement_text(customer_ref):
    ref=resolve_customer_ref(customer_ref)
    with get_db() as (_conn,cur):
        cur.execute('SELECT display_name,city FROM Customers WHERE id_card_number=%s',(ref,));name,area=cur.fetchone()
        cur.execute("SELECT COALESCE(r.printing_date,'') || ' ' || COALESCE(r.time,''), 'Credit sale #' || k.purchase_id, p.price_with_tax "
                    'FROM Customer_Khatoo k JOIN Purchase p ON p.id=k.purchase_id LEFT JOIN Receipt r ON r.purchase_id=p.id WHERE k.customer_id=%s',(ref,))
        entries=list(cur.fetchall())
        cur.execute("SELECT paid_at,'Payment: ' || payment_method,-amount FROM Credit_Payment WHERE customer_id=%s",(ref,));entries+=cur.fetchall()
        cur.execute("SELECT rv.created_at,'Payment correction',rv.amount FROM Credit_Payment_Reversal rv JOIN Credit_Payment cp ON cp.id=rv.payment_id WHERE cp.customer_id=%s",(ref,));entries+=cur.fetchall()
        cur.execute("SELECT cr.return_date || ' ' || cr.return_time,'Return: credit reduced', -(cr.refund_amount-COALESCE((SELECT SUM(rt.amount) FROM Refund_Transaction rt WHERE rt.return_id=cr.id),0)) "
                    "FROM Customer_Returns cr JOIN Purchase p ON p.id=cr.purchase_id WHERE cr.customer_id=%s AND p.payment_method='Khatoo Credit'",(ref,));entries+=cur.fetchall()
        cur.execute('SELECT COALESCE(SUM(amount_due),0) FROM Customer_Khatoo WHERE customer_id=%s',(ref,));due=_money(cur.fetchone()[0])
    lines=['CUSTOMER ACCOUNT STATEMENT',f'Customer: {name}',f'Area: {area or "—"}',f'Printed: {business_now():%Y-%m-%d %H:%M}', '-'*42]
    running=Decimal('0')
    for when,label,amount in sorted(entries,key=lambda entry:entry[0]):
        running+=_money(amount)
        lines.extend([f'{when} {label}',f'  Rs. {_money(amount):+.2f}   Balance: Rs. {running:.2f}'])
    lines+=['-'*42,f'CURRENT AMOUNT DUE: Rs. {due:.2f}']
    if running!=due:
        lines.append('Older adjustments exist. Current due is shown above.')
    return '\n'.join(lines)
