from core.business_time import business_date
from decimal import Decimal, ROUND_HALF_UP

from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoReports")


def _money(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_daily_sales_report(target_date=None):
    """Return a fast, tender-aware sales summary for one calendar date."""
    target_date = target_date or business_date().strftime("%Y-%m-%d")
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(p.price_with_tax), 0) "
                "FROM Purchase p JOIN Receipt r ON p.id = r.purchase_id "
                "WHERE r.printing_date = %s",
                (target_date,),
            )
            count_row = cur.fetchone() or (0, 0)
            cur.execute(
                "SELECT p.payment_method, COUNT(*), COALESCE(SUM(p.price_with_tax), 0) "
                "FROM Purchase p JOIN Receipt r ON p.id = r.purchase_id "
                "WHERE r.printing_date = %s GROUP BY p.payment_method",
                (target_date,),
            )
            tender_rows = cur.fetchall()
            cur.execute("SELECT COALESCE(SUM(refund_amount),0) FROM Customer_Returns WHERE return_date=%s", (target_date,))
            returns_total = _money(cur.fetchone()[0])
            cur.execute("SELECT payment_method,COALESCE(SUM(amount),0) FROM Refund_Transaction WHERE substr(created_at,1,10)=%s GROUP BY payment_method", (target_date,))
            refunds = {str(method): _money(amount) for method, amount in cur.fetchall()}

        breakdown = {
            "Cash": 0.0,
            "Credit Card": 0.0,
            "Easypaisa": 0.0,
            "JazzCash": 0.0,
            "Khatoo Credit": 0.0,
            "Other": 0.0,
        }
        transaction_breakdown = {key: 0 for key in breakdown}
        for method, txn_count, amount in tender_rows:
            key = str(method or "Cash").strip().lower()
            if key == "cash":
                bucket = "Cash"
            elif key in {"credit card", "card"}:
                bucket = "Credit Card"
            elif key == "easypaisa":
                bucket = "Easypaisa"
            elif key == "jazzcash":
                bucket = "JazzCash"
            elif "khatoo" in key or key in {"credit", "credit (khatoo)"}:
                bucket = "Khatoo Credit"
            else:
                bucket = "Other"
            breakdown[bucket] += _money(amount)
            transaction_breakdown[bucket] += int(txn_count or 0)

        digital_sales = breakdown["Credit Card"] + breakdown["Easypaisa"] + breakdown["JazzCash"]
        return {
            "date": target_date,
            "gross_sales": _money(count_row[1]),
            "returns_total": returns_total,
            "net_sales": _money(_money(count_row[1]) - returns_total),
            "cash_refunds": refunds.get("Cash", 0.0),
            "digital_refunds": _money(sum(amount for method, amount in refunds.items() if method != "Cash")),
            "refund_breakdown": refunds,
            "total_transactions": int(count_row[0] or 0),
            "total_sales": _money(count_row[1]),
            "cash_sales": _money(breakdown["Cash"]),
            "card_sales": _money(breakdown["Credit Card"]),
            "easypaisa_sales": _money(breakdown["Easypaisa"]),
            "jazzcash_sales": _money(breakdown["JazzCash"]),
            "digital_sales": _money(digital_sales),
            "credit_sales": _money(breakdown["Khatoo Credit"]),
            "other_sales": _money(breakdown["Other"]),
            "tender_breakdown": breakdown,
            "transaction_breakdown": transaction_breakdown,
        }
    except Exception as exc:
        logger.error("Get daily sales report error: %s", exc)
        raise RuntimeError("Sales report is unavailable. Check the shop connection and retry.") from exc


def get_credit_collections_report(target_date=None):
    """Return repayments of old customer credit, separate from new sales."""
    target_date = target_date or business_date().strftime("%Y-%m-%d")
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT payment_method, COUNT(*), COALESCE(SUM(amount), 0) "
                "FROM Credit_Payment WHERE substr(paid_at, 1, 10) = %s "
                "GROUP BY payment_method",
                (target_date,),
            )
            rows = cur.fetchall()
            cur.execute("SELECT payment_method,COALESCE(SUM(amount),0) FROM Credit_Payment_Reversal WHERE substr(created_at,1,10)=%s GROUP BY payment_method", (target_date,))
            reversals = {str(method): _money(amount) for method,amount in cur.fetchall()}
            cur.execute("SELECT payment_method,COALESCE(SUM(amount),0) FROM Refund_Transaction WHERE source_credit_payment_id IS NOT NULL AND substr(created_at,1,10)=%s GROUP BY payment_method", (target_date,))
            refunds = {str(method): _money(amount) for method,amount in cur.fetchall()}

        breakdown = {"Cash": 0.0, "Credit Card": 0.0, "Easypaisa": 0.0, "JazzCash": 0.0, "Other": 0.0}
        count = 0
        for method, txn_count, amount in rows:
            key = str(method or "Cash").strip().lower()
            if key == "cash":
                bucket = "Cash"
            elif key in {"credit card", "card"}:
                bucket = "Credit Card"
            elif key == "easypaisa":
                bucket = "Easypaisa"
            elif key == "jazzcash":
                bucket = "JazzCash"
            else:
                bucket = "Other"
            breakdown[bucket] += _money(amount)
            count += int(txn_count or 0)

        return {
            "date": target_date,
            "transactions": count,
            "gross_total": _money(sum(breakdown.values())),
            "refunds_total": _money(sum(refunds.values())),
            "reversals_total": _money(sum(reversals.values())),
            "net_total": _money(sum(breakdown.values()) - sum(refunds.values()) - sum(reversals.values())),
            "net_cash": _money(breakdown["Cash"] - refunds.get("Cash",0) - reversals.get("Cash",0)),
            "total": _money(sum(breakdown.values())),
            "cash": _money(breakdown["Cash"]),
            "digital": _money(breakdown["Credit Card"] + breakdown["Easypaisa"] + breakdown["JazzCash"]),
            "breakdown": breakdown,
        }
    except Exception as exc:
        logger.error("Get credit collections report error: %s", exc)
        raise RuntimeError("Credit collection report is unavailable. Retry before using its totals.") from exc


def get_expiry_alert_report(days_threshold=60):
    """Return in-stock batches expiring within the requested threshold."""
    try:
        threshold = max(0, int(days_threshold))
        today = business_date().isoformat()
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT p.product_name, b.id, b.quantity, b.expiry_date, p.category, p.rack_location, "
                "CAST(julianday(b.expiry_date) - julianday(%s) AS INTEGER) AS days_left "
                "FROM Batch b JOIN Products p ON b.product_id = p.id "
                "WHERE b.quantity > 0 "
                "AND julianday(b.expiry_date) - julianday(%s) <= %s "
                "ORDER BY b.expiry_date ASC",
                (today, today, threshold),
            )
            rows = cur.fetchall()

        return [
            {
                "product_name": p_name,
                "batch_id": batch_id,
                "quantity": qty,
                "expiry_date": str(expiry_date),
                "category": category or "General",
                "rack_location": rack or "Unassigned",
                "days_left": int(days_left),
            }
            for p_name, batch_id, qty, expiry_date, category, rack, days_left in rows
        ]
    except Exception as exc:
        logger.error("Get expiry alert report error: %s", exc)
        return []


def get_reorder_stock_report():
    """Return products whose aggregate stock is at or below their alert level."""
    try:
        with get_db() as (_conn, cur):
            cur.execute(
                "SELECT p.id,p.product_name,p.category,COALESCE(SUM(CASE WHEN b.quantity>0 AND b.expiry_date>=%s AND b.stock_status='SELLABLE' THEN b.quantity ELSE 0 END),0) AS sellable, "
                "p.min_stock,p.rack_location,p.price FROM Products p LEFT JOIN Batch b ON b.product_id=p.id "
                "WHERE p.is_active=1 GROUP BY p.id HAVING sellable<=p.min_stock ORDER BY sellable,p.product_name",
                (business_date().isoformat(),),
            )
            rows = cur.fetchall()

        return [
            {
                "product_id": pid,
                "product_name": name,
                "category": cat or "General",
                "stock_quantity": stock,
                "reorder_level": reorder if reorder is not None else 0,
                "rack_location": rack or "Unassigned",
                "unit_price": _money(price),
            }
            for pid, name, cat, stock, reorder, rack, price in rows
        ]
    except Exception as exc:
        logger.error("Get reorder stock report error: %s", exc)
        return []


def get_audit_log_report(limit=100):
    from core.audit_service import get_audit_logs
    safe_limit = max(1, min(int(limit), 500))
    rows = get_audit_logs(limit=safe_limit)
    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "username": row[2] or "System",
            "event_type": row[3],
            "description": row[4],
        }
        for row in rows
    ]
