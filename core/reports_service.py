from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoReports")


def get_daily_sales_report(target_date=None):
    """
    Computes sales breakdown for a specific date (defaults to today).
    Returns dict with metrics: total_sales, total_transactions, cash_sales, credit_sales.
    """
    if not target_date:
        target_date = date.today().strftime("%Y-%m-%d")
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT p.id, p.price_with_tax, p.payment_method, p.employee_id "
                "FROM Purchase p JOIN Receipt r ON p.id = r.purchase_id "
                "WHERE r.printing_date = %s",
                (target_date,),
            )
            purchases = cur.fetchall()

        total_sales_dec = Decimal("0.00")
        cash_sales_dec = Decimal("0.00")
        credit_sales_dec = Decimal("0.00")
        for _p_id, price, p_method, _emp_id in purchases:
            p_dec = Decimal(str(price or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_sales_dec += p_dec
            if "Credit" in str(p_method):
                credit_sales_dec += p_dec
            else:
                cash_sales_dec += p_dec

        return {
            "date": target_date,
            "total_transactions": len(purchases),
            "total_sales": float(total_sales_dec),
            "cash_sales": float(cash_sales_dec),
            "credit_sales": float(credit_sales_dec),
        }
    except Exception as e:
        logger.error(f"Get daily sales report error: {e}")
        return None


def get_expiry_alert_report(days_threshold=60):
    """
    Returns list of stock batches expiring within days_threshold or already expired.
    Dicts with keys: product_name, batch_id, quantity, expiry_date, category, rack_location, days_left.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT p.product_name, b.id, b.quantity, b.expiry_date, p.category, p.rack_location "
                "FROM Batch b JOIN Products p ON b.product_id = p.id "
                "WHERE b.quantity > 0 ORDER BY b.expiry_date ASC"
            )
            rows = cur.fetchall()

        today = date.today()
        report = []
        for p_name, b_id, qty, exp_str, cat, rack in rows:
            try:
                exp_dt = datetime.strptime(str(exp_str)[:10], "%Y-%m-%d").date()
                days_left = (exp_dt - today).days
            except Exception:
                days_left = 9999
            if days_left <= days_threshold:
                report.append({
                    "product_name": p_name,
                    "batch_id": b_id,
                    "quantity": qty,
                    "expiry_date": str(exp_str),
                    "category": cat or "General",
                    "rack_location": rack or "Unassigned",
                    "days_left": days_left,
                })
        return report
    except Exception as e:
        logger.error(f"Get expiry alert report error: {e}")
        return []


def get_reorder_stock_report():
    """
    Returns list of products whose total stock_quantity is at or below reorder_level.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, product_name, category, stock_quantity, reorder_level, rack_location, price "
                "FROM Products WHERE CAST(stock_quantity AS NUMERIC) <= CAST(reorder_level AS NUMERIC) "
                "ORDER BY CAST(stock_quantity AS NUMERIC) ASC"
            )
            rows = cur.fetchall()

        return [
            {
                "product_id": pid,
                "product_name": name,
                "category": cat or "General",
                "stock_quantity": stock,
                "reorder_level": reorder or 20,
                "rack_location": rack or "Unassigned",
                "unit_price": float(price or 0.0),
            }
            for pid, name, cat, stock, reorder, rack, price in rows
        ]
    except Exception as e:
        logger.error(f"Get reorder stock report error: {e}")
        return []


def get_audit_log_report(limit=100):
    """
    Returns recent system audit log events.
    """
    from core.audit_service import get_audit_logs
    rows = get_audit_logs(limit=limit)
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "username": r[2] or "System",
            "event_type": r[3],
            "description": r[4],
        }
        for r in rows
    ]
