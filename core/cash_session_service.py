from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from core.db_engine import get_db
from core.logger import get_logger
from core.audit_service import log_audit_event

logger = get_logger("PharmaKhaatoCashSession")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def open_session(employee_id, opening_cash=0.0):
    try:
        dec_open = _money(opening_cash)
        if dec_open < Decimal("0.00"):
            return False, "Opening cash float cannot be negative."
    except (ValueError, TypeError):
        return False, "Invalid opening cash float specified."

    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT id FROM Cash_Register_Session "
                "WHERE employee_id = %s AND status = 'OPEN'",
                (employee_id,),
            )
            if cur.fetchone():
                raise ValueError("A cash shift is already open for this staff member.")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO Cash_Register_Session (employee_id, opened_at, opening_cash, status) "
                "VALUES (%s, %s, %s, 'OPEN')",
                (employee_id, now_str, float(dec_open)),
            )
            session_id = cur.lastrowid
        log_audit_event(employee_id, "CASH_SESSION_OPENED", f"Opened cash shift with starting cash Rs.{dec_open:.2f}.")
        return True, session_id
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Open cash session error: %s", exc)
        return False, "The cash shift could not be started. Please try again."


def get_active_session(employee_id):
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT id, employee_id, opened_at, opening_cash, status "
                "FROM Cash_Register_Session "
                "WHERE employee_id = %s AND status = 'OPEN' ORDER BY id DESC LIMIT 1",
                (employee_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "employee_id": row[1], "opened_at": row[2], "opening_cash": float(row[3]), "status": row[4]}
    except Exception as exc:
        logger.error("Get active cash session error: %s", exc)
        return None


def record_cash_movement(session_id, employee_id, movement_type, amount, reason=""):
    movement_type = str(movement_type).upper().strip()
    if movement_type not in ("CASH_IN", "CASH_OUT", "REFUND"):
        return False, "Invalid cash-entry type."
    try:
        dec_amt = _money(amount)
        emp_id_int = int(employee_id)
        if dec_amt <= Decimal("0.00"):
            return False, "Cash amount must be greater than zero."
    except (ValueError, TypeError):
        return False, "Invalid cash-entry information."

    try:
        with get_db() as (_conn, cur):
            cur.execute("SELECT Employee_id FROM Employee WHERE Employee_id = %s", (emp_id_int,))
            if not cur.fetchone():
                raise ValueError("Your staff account could not be verified. Sign in again.")
            cur.execute("SELECT employee_id, status FROM Cash_Register_Session WHERE id = %s", (session_id,))
            sess = cur.fetchone()
            if not sess or sess[1] != "OPEN":
                raise ValueError("This cash shift is not open.")
            if int(sess[0]) != emp_id_int:
                raise ValueError("This cash shift belongs to another staff member.")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO Cash_Movement (session_id, employee_id, movement_type, amount, reason, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, emp_id_int, movement_type, float(dec_amt), reason or "N/A", now_str),
            )
        log_audit_event(employee_id, f"CASH_MOVEMENT_{movement_type}", f"Cash entry {movement_type}: Rs.{dec_amt:.2f} ({reason or 'No note'}).")
        return True, f"Cash entry of Rs.{dec_amt:.2f} saved."
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Record cash movement error: %s", exc)
        return False, "The cash entry could not be saved. Please try again."


def get_session_cash_summary(session_id):
    """Return only money that actually changes the physical drawer."""
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT employee_id, opened_at, opening_cash, status "
                "FROM Cash_Register_Session WHERE id = %s",
                (session_id,),
            )
            session = cur.fetchone()
            if not session:
                return None
            emp_id, opened_at, opening_cash_raw, status = session

            cur.execute(
                "SELECT COALESCE(SUM(p.price_with_tax), 0) "
                "FROM Purchase p JOIN Receipt r ON p.id = r.purchase_id "
                "WHERE p.employee_id = %s AND p.payment_method = 'Cash' "
                "AND (r.printing_date || ' ' || r.time) >= %s",
                (emp_id, opened_at),
            )
            cash_sales = _money((cur.fetchone() or [0])[0])

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM Credit_Payment "
                "WHERE session_id = %s AND payment_method = 'Cash'",
                (session_id,),
            )
            cash_credit_collections = _money((cur.fetchone() or [0])[0])

            cur.execute(
                "SELECT movement_type, COALESCE(SUM(amount), 0) "
                "FROM Cash_Movement WHERE session_id = %s GROUP BY movement_type",
                (session_id,),
            )
            movements = {row[0]: _money(row[1]) for row in cur.fetchall()}

        opening_cash = _money(opening_cash_raw)
        cash_in = movements.get("CASH_IN", Decimal("0.00"))
        cash_out = movements.get("CASH_OUT", Decimal("0.00"))
        refunds = movements.get("REFUND", Decimal("0.00"))
        expected = (opening_cash + cash_sales + cash_credit_collections + cash_in - cash_out - refunds).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "session_id": int(session_id),
            "status": status,
            "opening_cash": float(opening_cash),
            "cash_sales": float(cash_sales),
            "cash_credit_collections": float(cash_credit_collections),
            "cash_in": float(cash_in),
            "cash_out": float(cash_out),
            "refunds": float(refunds),
            "expected_cash": float(expected),
        }
    except Exception as exc:
        logger.error("Calculate cash summary error for session %s: %s", session_id, exc)
        return None


def calculate_expected_cash(session_id):
    summary = get_session_cash_summary(session_id)
    if not summary:
        return 0.0, 0.0, 0.0
    return summary["opening_cash"], summary["cash_sales"], summary["expected_cash"]


def close_session(session_id, closing_cash_actual, notes=""):
    try:
        dec_actual = _money(closing_cash_actual)
        if dec_actual < Decimal("0.00"):
            return False, "Counted cash cannot be negative."
    except (ValueError, TypeError):
        return False, "Invalid closing cash count."

    summary = get_session_cash_summary(session_id)
    if not summary:
        return False, "This cash shift could not be found."
    dec_expected = _money(summary["expected_cash"])
    discrepancy = (dec_actual - dec_expected).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    try:
        with get_db() as (_conn, cur):
            cur.execute("SELECT employee_id, status FROM Cash_Register_Session WHERE id = %s", (session_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("This cash shift could not be found.")
            if row[1] == "CLOSED":
                raise ValueError("This cash shift is already closed.")
            emp_id = row[0]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "UPDATE Cash_Register_Session SET closed_at = %s, closing_cash_actual = %s, "
                "expected_cash_system = %s, cash_discrepancy = %s, status = 'CLOSED', notes = %s "
                "WHERE id = %s",
                (now_str, float(dec_actual), float(dec_expected), float(discrepancy), notes, session_id),
            )

        if discrepancy > 0:
            disc_str = f"Over: +Rs.{discrepancy:.2f}"
        elif discrepancy < 0:
            disc_str = f"Short: -Rs.{abs(discrepancy):.2f}"
        else:
            disc_str = "Balanced (Rs. 0.00)"
        log_audit_event(emp_id, "CASH_SESSION_CLOSED", f"Closed cash shift. Expected Rs.{dec_expected:.2f}; actual Rs.{dec_actual:.2f}; {disc_str}.")
        return True, {**summary, "actual_cash": float(dec_actual), "discrepancy": float(discrepancy), "closed_at": now_str}
    except ValueError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Close cash session error: %s", exc)
        return False, "The cash shift could not be closed. Please try again."
