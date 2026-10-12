import json
from datetime import datetime
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoHoldSale")


def hold_sale(customer_id, employee_id, cart, note=""):
    """
    Puts an active checkout sale on hold.
    Returns (success: bool, msg_or_id).
    """
    if not cart:
        return False, "Cart is empty. Cannot hold an empty cart."
    try:
        emp_id_int = int(employee_id)
    except (ValueError, TypeError):
        return False, f"Invalid employee ID '{employee_id}'. Cannot hold sale."

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT Employee_id FROM Employee WHERE Employee_id = %s", (emp_id_int,))
            if not cur.fetchone():
                raise ValueError(f"Employee ID #{emp_id_int} not found. Please log in again.")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cart_json = json.dumps(cart)
            cur.execute(
                "INSERT INTO Hold_Sales (hold_time, customer_id, employee_id, cart_json, note) "
                "VALUES (%s, %s, %s, %s, %s)",
                (now_str, str(customer_id or "GUEST_WALK_IN"), emp_id_int, cart_json, str(note)),
            )
            hold_id = cur.lastrowid
        logger.info(f"Sale #{hold_id} put on hold by employee #{employee_id}")
        return True, hold_id
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        logger.error(f"Hold sale error: {e}")
        return False, f"Failed to hold sale: {e}"


def get_held_sales():
    """
    Returns list of all pending held sales tuples:
    (id, hold_time, customer_id, employee_id, cart_json, note)
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, hold_time, customer_id, employee_id, cart_json, note "
                "FROM Hold_Sales ORDER BY id DESC"
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Get held sales error: {e}")
        return []


def recall_sale(hold_id):
    """
    Recalls a held sale by ID and removes it from the pending hold queue.
    Returns (success: bool, cart_data_or_msg).
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT customer_id, cart_json, note FROM Hold_Sales WHERE id = %s", (hold_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Hold sale #{hold_id} not found.")
            cust_id, cart_json, note = row[0], row[1], row[2]
            cart = json.loads(cart_json)
            cur.execute("DELETE FROM Hold_Sales WHERE id = %s", (hold_id,))
        logger.info(f"Recalled sale #{hold_id}")
        return True, {"customer_id": cust_id, "cart": cart, "note": note}
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        logger.error(f"Recall sale error: {e}")
        return False, f"Failed to recall sale: {e}"
