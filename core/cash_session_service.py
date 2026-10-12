from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from core.db_engine import get_db
from core.logger import get_logger
from core.audit_service import log_audit_event

logger = get_logger("PharmaKhaatoCashSession")


def open_session(employee_id, opening_cash=0.0):
    """
    Opens a new cash register session for an employee.
    Enforces that an employee can only have one active OPEN session at a time.
    """
    try:
        dec_open = Decimal(str(opening_cash)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if dec_open < Decimal("0.00"):
            return False, "Opening cash float cannot be negative."
    except (ValueError, TypeError):
        return False, "Invalid opening cash float specified."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, opened_at FROM Cash_Register_Session "
                "WHERE employee_id = %s AND status = 'OPEN'",
                (employee_id,),
            )
            existing = cur.fetchone()
            if existing:
                raise ValueError(
                    f"Employee #{employee_id} already has an active register session "
                    f"(Session #{existing[0]} opened at {existing[1]})."
                )
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO Cash_Register_Session (employee_id, opened_at, opening_cash, status) "
                "VALUES (%s, %s, %s, 'OPEN')",
                (employee_id, now_str, float(dec_open)),
            )
            session_id = cur.lastrowid
        log_audit_event(
            employee_id, "CASH_SESSION_OPENED",
            f"Opened Cash Register Session #{session_id} with float Rs.{dec_open:.2f}",
        )
        return True, session_id
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        logger.error(f"Open cash session error: {e}")
        return False, f"Failed to open session: {e}"


def get_active_session(employee_id):
    """
    Returns active OPEN cash register session dictionary for an employee, or None.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, employee_id, opened_at, opening_cash, status "
                "FROM Cash_Register_Session "
                "WHERE employee_id = %s AND status = 'OPEN' ORDER BY id DESC LIMIT 1",
                (employee_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "employee_id": row[1],
            "opened_at": row[2],
            "opening_cash": float(row[3]),
            "status": row[4],
        }
    except Exception as e:
        logger.error(f"Get active cash session error: {e}")
        return None


def record_cash_movement(session_id, employee_id, movement_type, amount, reason=""):
    """
    Records cash in, cash out, or refund cash movement for a session.
    movement_type: 'CASH_IN', 'CASH_OUT', 'REFUND'
    """
    movement_type = str(movement_type).upper().strip()
    if movement_type not in ("CASH_IN", "CASH_OUT", "REFUND"):
        return False, "Invalid movement type. Allowed: CASH_IN, CASH_OUT, REFUND."
    try:
        dec_amt = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if dec_amt <= Decimal("0.00"):
            return False, "Movement amount must be greater than zero."
    except (ValueError, TypeError):
        return False, "Invalid monetary amount."

    try:
        emp_id_int = int(employee_id)
    except (ValueError, TypeError):
        return False, f"Invalid employee ID '{employee_id}'. Cannot record cash movement."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id FROM Employee WHERE Employee_id = %s", (emp_id_int,)
            )
            if not cur.fetchone():
                raise ValueError(f"Employee ID #{emp_id_int} not found. Please log in again.")
            cur.execute(
                "SELECT id, status FROM Cash_Register_Session WHERE id = %s", (session_id,)
            )
            sess = cur.fetchone()
            if not sess or sess[1] != "OPEN":
                raise ValueError(f"Cash session #{session_id} is not open.")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO Cash_Movement "
                "(session_id, employee_id, movement_type, amount, reason, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, emp_id_int, movement_type, float(dec_amt), reason or "N/A", now_str),
            )
        log_audit_event(
            employee_id, f"CASH_MOVEMENT_{movement_type}",
            f"Session #{session_id} cash movement {movement_type}: Rs.{dec_amt:.2f} ({reason})",
        )
        return True, f"Cash movement {movement_type} of Rs.{dec_amt:.2f} recorded."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        logger.error(f"Record cash movement error: {e}")
        return False, f"Failed to record movement: {e}"


def calculate_expected_cash(session_id):
    """
    Calculates expected cash in drawer for session_id.
    Formula: Opening Float + Cash Sales + Cash In - Cash Out - Cash Refunds.
    Returns (opening_cash: float, cash_sales: float, expected_total: float).
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT employee_id, opened_at, opening_cash, status "
                "FROM Cash_Register_Session WHERE id = %s",
                (session_id,),
            )
            session = cur.fetchone()
            if not session:
                return 0.0, 0.0, 0.0
            emp_id, opened_at, opening_cash_raw, _status = session
            opening_cash = Decimal(str(opening_cash_raw))

            cur.execute(
                "SELECT SUM(p.price_with_tax) FROM Purchase p "
                "JOIN Receipt r ON p.id = r.purchase_id "
                "WHERE p.employee_id = %s AND p.payment_method IN ('Cash', 'Credit Card', 'Easypaisa', 'JazzCash') "
                "  AND (r.printing_date || ' ' || r.time) >= %s",
                (emp_id, opened_at),
            )
            res = cur.fetchone()
            cash_sales = Decimal(str(res[0])) if (res and res[0] is not None) else Decimal("0.00")

            cur.execute(
                "SELECT movement_type, SUM(amount) FROM Cash_Movement "
                "WHERE session_id = %s GROUP BY movement_type",
                (session_id,),
            )
            movements = {row[0]: Decimal(str(row[1] or 0.0)) for row in cur.fetchall()}

        cash_in = movements.get("CASH_IN", Decimal("0.00"))
        cash_out = movements.get("CASH_OUT", Decimal("0.00"))
        cash_refunds = movements.get("REFUND", Decimal("0.00"))
        expected_total = (opening_cash + cash_sales + cash_in - cash_out - cash_refunds).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return float(opening_cash), float(cash_sales), float(expected_total)
    except Exception as e:
        logger.error(f"Calculate expected cash error for session #{session_id}: {e}")
        return 0.0, 0.0, 0.0


def close_session(session_id, closing_cash_actual, notes=""):
    """
    Closes an active cash session, calculates cash discrepancy (actual - expected),
    and records closing details.
    """
    try:
        dec_actual = Decimal(str(closing_cash_actual)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if dec_actual < Decimal("0.00"):
            return False, "Actual cash counted cannot be negative."
    except (ValueError, TypeError):
        return False, "Invalid closing cash count specified."

    opening_cash, cash_sales, expected_cash = calculate_expected_cash(session_id)
    dec_expected = Decimal(str(expected_cash)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discrepancy = (dec_actual - dec_expected).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT employee_id, status FROM Cash_Register_Session WHERE id = %s", (session_id,)
            )
            s_row = cur.fetchone()
            if not s_row:
                raise ValueError("Session record not found.")
            if s_row[1] == "CLOSED":
                raise ValueError("Session is already closed.")
            emp_id = s_row[0]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "UPDATE Cash_Register_Session "
                "SET closed_at = %s, closing_cash_actual = %s, expected_cash_system = %s, "
                "    cash_discrepancy = %s, status = 'CLOSED', notes = %s "
                "WHERE id = %s",
                (now_str, float(dec_actual), float(dec_expected), float(discrepancy), notes, session_id),
            )

        disc_str = (
            f"Over: +Rs.{discrepancy:.2f}" if discrepancy > Decimal("0.00")
            else (f"Short: -Rs.{abs(discrepancy):.2f}" if discrepancy < Decimal("0.00")
                  else "Perfect (Rs. 0.00)")
        )
        log_audit_event(
            emp_id, "CASH_SESSION_CLOSED",
            f"Closed Session #{session_id}. Expected: Rs.{dec_expected:.2f}, "
            f"Actual: Rs.{dec_actual:.2f}, Discrepancy: {disc_str}",
        )
        return True, {
            "session_id": session_id,
            "opening_cash": opening_cash,
            "cash_sales": cash_sales,
            "expected_cash": float(dec_expected),
            "actual_cash": float(dec_actual),
            "discrepancy": float(discrepancy),
            "closed_at": now_str,
        }
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        logger.error(f"Close cash session error: {e}")
        return False, f"Failed to close session: {e}"
