"""Small supplier invoice/dues ledger, posted with its stock in one transaction."""
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP

from core.business_time import business_now, business_date
from core.db_engine import get_db
from core.permission_service import require_permission
from core.unit_service import whole_quantity, convert_quantity, resolve_unit


def _minor(value):
    value=Decimal(str(value))
    if not value.is_finite() or value<0 or value>1_000_000_000:
        raise ValueError('Enter a valid nonnegative amount.')
    return int((value*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))


def _authorize(employee_id):
    allowed,message=require_permission(employee_id,'inventory.manage')
    if not allowed:
        raise ValueError(message)


def _prior(cur,operation_id,employee_id,payload):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',str(operation_id)):
        raise ValueError('Save the supplier request before submitting it.')
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()
    cur.execute('SELECT employee_id,fingerprint,result_json FROM Supplier_Operation WHERE operation_id=%s',(operation_id,))
    row=cur.fetchone()
    if row:
        if int(row[0])!=int(employee_id) or row[1]!=fingerprint:
            raise ValueError('This supplier request belongs to different information.')
        return fingerprint,json.loads(row[2])
    return fingerprint,None


def _save(cur,operation_id,employee_id,fingerprint,result):
    cur.execute('INSERT INTO Supplier_Operation VALUES(%s,%s,%s,%s)',
                (operation_id,employee_id,fingerprint,json.dumps(result)))
    cur.execute("INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES(%s,%s,'SUPPLIER_ACCOUNT_POSTED',%s)",
                (business_now().isoformat(timespec='seconds'),str(employee_id),json.dumps(result)))


def _due(cur,supplier_id):
    cur.execute('SELECT COALESCE(SUM(total_minor),0) FROM Supplier_Invoice WHERE supplier_id=%s',(supplier_id,))
    invoices=int(cur.fetchone()[0])
    cur.execute('SELECT COALESCE(SUM(amount_minor),0) FROM Supplier_Payment WHERE supplier_id=%s',(supplier_id,))
    paid=int(cur.fetchone()[0])
    cur.execute('SELECT COALESCE(SUM(r.credit_minor),0) FROM Supplier_Return r JOIN Supplier_Invoice_Line l ON l.id=r.invoice_line_id '
                'JOIN Supplier_Invoice i ON i.id=l.invoice_id WHERE i.supplier_id=%s',(supplier_id,))
    return invoices-paid-int(cur.fetchone()[0])


def _payment(cur,supplier_id,minor,method,employee_id,terminal_id,note,invoice_id=None):
    allowed={'Cash from drawer','Bank transfer','Outside drawer'}
    if method not in allowed:
        raise ValueError('Choose Cash from drawer, Bank transfer, or Outside drawer.')
    session_id=None
    now=business_now().isoformat(timespec='seconds')
    if method=='Cash from drawer':
        cur.execute("SELECT id FROM Cash_Register_Session WHERE employee_id=%s AND terminal_id=%s AND status='OPEN'",
                    (employee_id,terminal_id or 'local'))
        row=cur.fetchone()
        if not row:
            raise ValueError('Start a cash shift before paying a supplier from this drawer.')
        session_id=int(row[0])
        from core.cash_session_service import _session_summary
        if _minor(_session_summary(cur,session_id)['expected_cash']) < minor:
            raise ValueError('The recorded drawer cash is too low. Add the physical cash first or choose Outside drawer.')
        cur.execute("INSERT INTO Cash_Movement(session_id,employee_id,movement_type,amount,reason,created_at) VALUES(%s,%s,'CASH_OUT',%s,%s,%s)",
                    (session_id,employee_id,minor/100,'Supplier payment: '+str(note)[:180],now))
    cur.execute('INSERT INTO Supplier_Payment(supplier_id,invoice_id,amount_minor,payment_method,employee_id,session_id,created_at,note) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                (supplier_id,invoice_id,minor,method,employee_id,session_id,now,str(note)[:250]))
    return cur.lastrowid


def receive_invoice(supplier_id,reference,lines,employee_id,*,operation_id,paid_amount=0,payment_method='Bank transfer',terminal_id=None):
    try:
        _authorize(employee_id)
        reference=str(reference).strip()
        if not reference or len(reference)>100 or not isinstance(lines,list) or not 1<=len(lines)<=100:
            raise ValueError('Choose a supplier, enter its invoice number, and add at least one stock line.')
        payload=['invoice',int(supplier_id),reference,lines,str(paid_amount),payment_method,terminal_id or 'local']
        with get_db(immediate=True) as (_conn,cur):
            fingerprint,previous=_prior(cur,operation_id,employee_id,payload)
            if previous:
                return True,'This supplier invoice was already saved.',previous
            cur.execute('SELECT id FROM Supplier WHERE id=%s',(supplier_id,))
            if not cur.fetchone():
                raise ValueError('Choose an existing supplier.')
            cur.execute('SELECT id FROM Supplier_Invoice WHERE supplier_id=%s AND reference=%s',(supplier_id,reference))
            if cur.fetchone():
                raise ValueError('This supplier invoice number is already saved. Check its history rather than receiving it twice.')
            cur.execute('INSERT INTO Supplier_Invoice(supplier_id,reference,invoice_date,total_minor,employee_id) VALUES(%s,%s,%s,0,%s)',
                        (supplier_id,reference,business_date().isoformat(),employee_id))
            invoice_id=cur.lastrowid
            total=0
            from core.inventory_service import add_batch
            for index,line in enumerate(lines):
                product=int(line['product_id'])
                quantity=whole_quantity(line['quantity'])
                unit=line.get('unit_code','base')
                multiplier=resolve_unit(product,unit,cur=cur)['multiplier']
                cost=Decimal(str(line['cost_per_unit']))
                line_minor=_minor(cost*quantity)
                bonus=whole_quantity(line.get('bonus_base_units',0),allow_zero=True)
                base_quantity=convert_quantity(product,quantity,unit,cur)+bonus
                ok,message=add_batch(product,supplier_id,base_quantity,line['expiry'],
                    lot_number=line.get('lot',''),expiry_precision=line.get('expiry_precision','MONTH'),
                    cost_price=float(Decimal(line_minor)/100/base_quantity),sale_price=line.get('sale_price'),mrp=line.get('mrp'),
                    invoice_reference=reference,employee_id=employee_id,operation_key=f'{operation_id}-{index}')
                if not ok:
                    raise ValueError(message)
                cur.execute('SELECT batch_id FROM Stock_Operation WHERE operation_key=%s',(f'{operation_id}-{index}',))
                batch_id=cur.fetchone()[0]
                cur.execute('INSERT INTO Supplier_Invoice_Line(invoice_id,batch_id,quantity,total_minor) VALUES(%s,%s,%s,%s)',
                            (invoice_id,batch_id,base_quantity,line_minor))
                total+=line_minor
            paid=_minor(paid_amount)
            if paid>total:
                raise ValueError('The payment exceeds this supplier invoice. Enter the amount actually paid.')
            cur.execute('UPDATE Supplier_Invoice SET total_minor=%s WHERE id=%s',(total,invoice_id))
            if paid:
                _payment(cur,supplier_id,paid,payment_method,employee_id,terminal_id,reference,invoice_id)
            result={'invoice_id':invoice_id,'total':total/100,'paid':paid/100,'balance':_due(cur,supplier_id)/100}
            _save(cur,operation_id,employee_id,fingerprint,result)
        return True,'Stock and supplier invoice saved.',result
    except (ValueError,TypeError,KeyError,ArithmeticError) as exc:
        return False,str(exc),None


def pay_supplier(supplier_id,amount,employee_id,*,operation_id,payment_method='Bank transfer',note='',terminal_id=None):
    try:
        _authorize(employee_id)
        minor=_minor(amount)
        if minor<=0:
            raise ValueError('Enter a payment greater than zero.')
        payload=['payment',int(supplier_id),minor,payment_method,str(note),terminal_id or 'local']
        with get_db(immediate=True) as (_conn,cur):
            fingerprint,previous=_prior(cur,operation_id,employee_id,payload)
            if previous:
                return True,'This supplier payment was already saved.',previous
            if minor>_due(cur,supplier_id):
                raise ValueError('This amount exceeds the supplier balance. Check the account first.')
            payment_id=_payment(cur,supplier_id,minor,payment_method,employee_id,terminal_id,note)
            result={'payment_id':payment_id,'balance':_due(cur,supplier_id)/100}
            _save(cur,operation_id,employee_id,fingerprint,result)
        return True,'Supplier payment saved.',result
    except (ValueError,TypeError,ArithmeticError) as exc:
        return False,str(exc),None


def supplier_accounts():
    with get_db() as (_conn,cur):
        cur.execute('SELECT id,supplier_name FROM Supplier ORDER BY supplier_name LIMIT 500')
        suppliers=cur.fetchall()
        return [{'supplier_id':sid,'name':name,'balance':_due(cur,sid)/100} for sid,name in suppliers]


def supplier_history(supplier_id):
    with get_db() as (_conn,cur):
        cur.execute("SELECT invoice_date,reference,total_minor/100.0,'Invoice' FROM Supplier_Invoice WHERE supplier_id=%s "
                    "UNION ALL SELECT created_at,note,-amount_minor/100.0,'Payment' FROM Supplier_Payment WHERE supplier_id=%s "
                    "UNION ALL SELECT r.created_at,r.reason,-r.credit_minor/100.0,'Return credit' FROM Supplier_Return r "
                    "JOIN Supplier_Invoice_Line l ON l.id=r.invoice_line_id JOIN Supplier_Invoice i ON i.id=l.invoice_id WHERE i.supplier_id=%s "
                    "ORDER BY 1 DESC LIMIT 500",(supplier_id,supplier_id,supplier_id))
        return cur.fetchall()


def invoice_lines(supplier_id):
    with get_db() as (_conn,cur):
        cur.execute('SELECT l.id,i.reference,p.product_name,b.lot_number,l.quantity,'
                    'COALESCE((SELECT SUM(r.quantity) FROM Supplier_Return r WHERE r.invoice_line_id=l.id),0),'
                    'b.quantity,b.expiry_date FROM Supplier_Invoice_Line l JOIN Supplier_Invoice i ON i.id=l.invoice_id '
                    'JOIN Batch b ON b.id=l.batch_id JOIN Products p ON p.id=b.product_id '
                    'WHERE i.supplier_id=%s ORDER BY l.id DESC LIMIT 500',(supplier_id,))
        return cur.fetchall()


def return_to_supplier(line_id,quantity,reason,employee_id,*,operation_id):
    try:
        _authorize(employee_id)
        qty=whole_quantity(quantity)
        reason=str(reason).strip()
        if len(reason)<3:
            raise ValueError('Enter a short reason for the supplier return.')
        payload=['supplier-return',int(line_id),qty,reason]
        with get_db(immediate=True) as (_conn,cur):
            fingerprint,previous=_prior(cur,operation_id,employee_id,payload)
            if previous:
                return True,'This supplier return was already saved.',previous
            cur.execute('SELECT l.batch_id,l.quantity,l.total_minor,i.supplier_id,b.product_id,b.quantity '
                        'FROM Supplier_Invoice_Line l JOIN Supplier_Invoice i ON i.id=l.invoice_id '
                        'JOIN Batch b ON b.id=l.batch_id WHERE l.id=%s',(line_id,))
            line=cur.fetchone()
            if not line:
                raise ValueError('Choose a received supplier invoice line.')
            cur.execute('SELECT COALESCE(SUM(quantity),0),COALESCE(SUM(credit_minor),0) FROM Supplier_Return WHERE invoice_line_id=%s',(line_id,))
            prior_qty,prior_credit=cur.fetchone()
            if qty>line[1]-prior_qty or qty>line[5]:
                raise ValueError('That quantity is no longer available to return to the supplier.')
            credit=line[2]-prior_credit if qty==line[1]-prior_qty else min(
                int((Decimal(line[2])*qty/line[1]).quantize(Decimal('1'),rounding=ROUND_HALF_UP)),line[2]-prior_credit)
            now=business_now().isoformat(timespec='seconds')
            cur.execute('INSERT INTO Supplier_Return(invoice_line_id,quantity,credit_minor,employee_id,created_at,reason) VALUES(%s,%s,%s,%s,%s,%s)',
                        (line_id,qty,credit,employee_id,now,reason))
            return_id=cur.lastrowid
            cur.execute('UPDATE Batch SET quantity=quantity-%s WHERE id=%s AND quantity>=%s',(qty,line[0],qty))
            if cur.rowcount!=1:
                raise ValueError('Stock changed. Recheck the supplier return.')
            cur.execute('UPDATE Products SET stock_quantity=stock_quantity-%s WHERE id=%s AND stock_quantity>=%s',(qty,line[4],qty))
            if cur.rowcount!=1:
                raise ValueError('The stock totals need an owner review before this return.')
            cur.execute("INSERT INTO Stock_Movement(product_id,batch_id,quantity_delta,movement_type,reason,employee_id,operation_key,created_at) VALUES(%s,%s,%s,'SUPPLIER_RETURN',%s,%s,%s,%s)",
                        (line[4],line[0],-qty,reason,employee_id,operation_id,now))
            result={'return_id':return_id,'credit':credit/100,'balance':_due(cur,line[3])/100}
            _save(cur,operation_id,employee_id,fingerprint,result)
        from core.inventory_service import clear_inventory_cache
        clear_inventory_cache()
        return True,'Supplier return and credit saved.',result
    except (ValueError,TypeError,ArithmeticError) as exc:
        return False,str(exc),None
