from core.business_time import business_date, business_now
from decimal import Decimal, InvalidOperation
import json
import hashlib
import re

from core.db_engine import get_db
from core.logger import get_logger
from core.money import checked_money
from core.audit_service import log_audit_event
from core.permission_service import require_permission

logger = get_logger("PharmaKhaatoCashSession")


def _money(value) -> Decimal:
    return checked_money(value)


def open_session(employee_id, opening_cash=0.0, terminal_id=None, operation_id=None):
    try:
        terminal_id = _terminal(terminal_id)
        employee_id = int(employee_id)
        dec_open = _money(opening_cash)
        if dec_open < Decimal("0.00"):
            return False, "Opening cash float cannot be negative."
    except (ValueError, TypeError, InvalidOperation):
        return False, "Invalid opening cash float specified."

    allowed, reason = require_permission(employee_id, "cash.own_shift")
    if not allowed:
        return False, reason

    try:
        with get_db(immediate=True) as (_conn, cur):
            payload = ['open', str(dec_open), terminal_id]
            saved = _operation(cur, operation_id, employee_id, payload)
            if saved is not None:
                return saved
            cur.execute(
                "SELECT id FROM Cash_Register_Session "
                "WHERE terminal_id = %s AND status = 'OPEN'",
                (terminal_id,),
            )
            if cur.fetchone():
                raise ValueError("A cash shift is already open for this counter.")
            now_str = business_now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO Cash_Register_Session (employee_id, opened_at, opening_cash, status, terminal_id) "
                "VALUES (%s, %s, %s, 'OPEN', %s)",
                (employee_id, now_str, float(dec_open), terminal_id),
            )
            session_id = cur.lastrowid
            _save_operation(cur, operation_id, employee_id, payload, [True, session_id])
        log_audit_event(employee_id, "CASH_SESSION_OPENED", f"Opened cash shift with starting cash Rs.{dec_open:.2f}.")
        return True, session_id
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Open cash session error: %s", exc)
        return False, "The cash shift could not be started. Please try again."


def get_active_session(employee_id, terminal_id=None):
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT id, employee_id, opened_at, opening_cash, status, terminal_id "
                "FROM Cash_Register_Session "
                "WHERE employee_id = %s AND terminal_id = %s AND status = 'OPEN' ORDER BY id DESC LIMIT 1",
                (employee_id,_terminal(terminal_id)),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "employee_id": row[1], "opened_at": row[2], "opening_cash": float(row[3]), "status": row[4], "terminal_id": row[5]}
    except Exception as exc:
        logger.error("Get active cash session error: %s", exc)
        return None


def record_cash_movement(session_id, employee_id, movement_type, amount, reason="", operation_id=None, terminal_id=None):
    movement_type = str(movement_type).upper().strip()
    if movement_type not in ("CASH_IN", "CASH_OUT", "REFUND"):
        return False, "Invalid cash-entry type."
    try:
        session_id = int(session_id)
        employee_id = int(employee_id)
        dec_amt = _money(amount)
        if dec_amt <= Decimal("0.00"):
            return False, "Cash amount must be greater than zero."
    except (ValueError, TypeError, InvalidOperation):
        return False, "Invalid cash-entry information."

    allowed, permission_reason = require_permission(employee_id, "cash.own_shift")
    if not allowed:
        return False, permission_reason

    try:
        with get_db(immediate=True) as (_conn, cur):
            saved = _operation(cur,operation_id,employee_id,["movement",session_id,movement_type,str(dec_amt),str(reason),_terminal(terminal_id)])
            if saved is not None:
                return saved
            cur.execute("SELECT employee_id, status,terminal_id FROM Cash_Register_Session WHERE id = %s", (session_id,))
            sess = cur.fetchone()
            if not sess or sess[1] != "OPEN":
                raise ValueError("This cash shift is not open.")
            if int(sess[0]) != employee_id or sess[2] != _terminal(terminal_id):
                raise ValueError("This cash shift belongs to another staff member or counter.")
            now_str = business_now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO Cash_Movement (session_id, employee_id, movement_type, amount, reason, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, employee_id, movement_type, float(dec_amt), reason or "N/A", now_str),
            )
            _save_operation(cur,operation_id,employee_id,["movement",session_id,movement_type,str(dec_amt),str(reason),_terminal(terminal_id)],[True,f"Cash entry of Rs.{dec_amt:.2f} saved."])
        log_audit_event(employee_id, f"CASH_MOVEMENT_{movement_type}", f"Cash entry {movement_type}: Rs.{dec_amt:.2f} ({reason or 'No note'}).")
        return True, f"Cash entry of Rs.{dec_amt:.2f} saved."
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Record cash movement error: %s", exc)
        return False, "The cash entry could not be saved. Please try again."


def _session_summary(cur, session_id):
    cur.execute("SELECT opening_cash,status FROM Cash_Register_Session WHERE id=%s",(session_id,))
    row=cur.fetchone()
    if not row:
        return None
    opening=_money(row[0])
    cur.execute("SELECT COALESCE(SUM(price_with_tax),0) FROM Purchase WHERE session_id=%s AND payment_method='Cash'",(session_id,))
    sales=_money(cur.fetchone()[0])
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM Credit_Payment WHERE session_id=%s AND payment_method='Cash'",(session_id,))
    collections=_money(cur.fetchone()[0])
    cur.execute("SELECT movement_type,COALESCE(SUM(amount),0) FROM Cash_Movement WHERE session_id=%s GROUP BY movement_type",(session_id,))
    movements={kind:_money(amount) for kind,amount in cur.fetchall()}
    cash_in=movements.get("CASH_IN",Decimal(0));cash_out=movements.get("CASH_OUT",Decimal(0));refunds=movements.get("REFUND",Decimal(0))
    return {"session_id":int(session_id),"status":row[1],"opening_cash":float(opening),"cash_sales":float(sales),
            "cash_credit_collections":float(collections),"cash_in":float(cash_in),"cash_out":float(cash_out),
            "refunds":float(refunds),"expected_cash":float(opening+sales+collections+cash_in-cash_out-refunds)}


def get_session_cash_summary(session_id):
    # All totals come from one consistent read transaction. Database errors are
    # unknown, never fabricated zero cash.
    with get_db() as (_conn,cur):
        return _session_summary(cur,session_id)


def calculate_expected_cash(session_id):
    summary = get_session_cash_summary(session_id)
    if not summary:
        raise ValueError("This cash shift could not be found.")
    return summary["opening_cash"], summary["cash_sales"], summary["expected_cash"]


def close_session(session_id, closing_cash_actual, notes="", employee_id=None, terminal_id=None, operation_id=None):
    try:
        employee_id=int(employee_id)
        session_id=int(session_id)
        terminal_id=_terminal(terminal_id)
        actual=_money(closing_cash_actual)
        if actual < 0:
            raise ValueError("Counted cash cannot be negative.")
        allowed,reason=require_permission(employee_id,"cash.own_shift")
        if not allowed:
            raise ValueError(reason)
        payload=["close",session_id,str(actual),str(notes),terminal_id]
        with get_db(immediate=True) as (_conn,cur):
            saved=_operation(cur,operation_id,employee_id,payload)
            if saved is not None:
                return saved
            cur.execute("SELECT employee_id,status,terminal_id FROM Cash_Register_Session WHERE id=%s",(session_id,))
            row=cur.fetchone()
            if not row or int(row[0]) != employee_id or row[2] != terminal_id:
                raise ValueError("This cash shift belongs to another staff member or counter.")
            if row[1] != "OPEN":
                raise ValueError("This cash shift is already closed.")
            summary=_session_summary(cur,session_id)
            expected=_money(summary["expected_cash"])
            discrepancy=actual-expected
            now=business_now().isoformat(timespec="seconds")
            cur.execute("UPDATE Cash_Register_Session SET closed_at=%s,closing_cash_actual=%s,expected_cash_system=%s,cash_discrepancy=%s,status='CLOSED',notes=%s WHERE id=%s AND status='OPEN'",
                        (now,float(actual),float(expected),float(discrepancy),str(notes)[:500],session_id))
            result=[True,{**summary,"status":"CLOSED","actual_cash":float(actual),"discrepancy":float(discrepancy),"closed_at":now}]
            _save_operation(cur,operation_id,employee_id,payload,result)
            cur.execute("INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES(%s,%s,'CASH_SESSION_CLOSED',%s)",
                        (now,str(employee_id),f"Closed shift #{session_id}; expected Rs.{expected:.2f}, actual Rs.{actual:.2f}."))
        return tuple(result)
    except (ValueError,TypeError,InvalidOperation) as exc:
        return False,str(exc) if employee_id is not None else "Sign in again before closing this cash shift."
    except Exception:
        logger.exception("Cash shift result could not be confirmed")
        return False,"Cash shift result could not be confirmed. Refresh its status before trying again."


def _terminal(terminal_id):
    value=str(terminal_id or "local")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",value):
        raise ValueError("Invalid counter identity.")
    return value


def _fingerprint(payload):
    return hashlib.sha256(json.dumps(payload,separators=(",",":"),sort_keys=True).encode()).hexdigest()


def _operation(cur,operation_id,employee_id,payload):
    if operation_id is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",str(operation_id)):
        raise ValueError("Invalid cash-entry request identity.")
    cur.execute("SELECT employee_id,request_fingerprint,result_json FROM Cash_Operation WHERE operation_id=%s",(operation_id,))
    row=cur.fetchone()
    if row:
        if int(row[0])!=int(employee_id) or row[1]!=_fingerprint(payload):
            raise ValueError("This cash request was already used for a different entry.")
        return tuple(json.loads(row[2]))
    return None


def _save_operation(cur,operation_id,employee_id,payload,result):
    if operation_id is not None:
        cur.execute("INSERT INTO Cash_Operation(operation_id,employee_id,request_fingerprint,result_json,created_at) VALUES(%s,%s,%s,%s,%s)",
                    (operation_id,employee_id,_fingerprint(payload),json.dumps(result),business_now().isoformat()))
