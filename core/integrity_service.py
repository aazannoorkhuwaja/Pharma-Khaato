"""Read-only reconciliation of the business facts a pharmacy must be able to trust.

Each check re-derives one fact from the rows that are supposed to prove it and
reports a disagreement. Nothing is written and nothing is repaired.

The identities below are the ones every write path in the product maintains
transactionally — checkout, returns, credit repayments and cash shifts — so a
finding means real damage: a partially restored backup, a database edited outside
the application, or residue from a much older schema. They were measured against
a live demo shop and a scripted shop with a discount, a credit sale, a cash
repayment and a closed shift before being asserted here, so they do not raise
false alarms on healthy data.

``TOLERANCE`` exists because each stored value is rounded to two decimal places
individually; a sale split across several lots can therefore absorb a cent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from core.business_time import business_now
from core.db_engine import get_db
from core.logger import get_logger

logger = get_logger("PharmaKhaatoIntegrity")

TOLERANCE = 0.02
_SAMPLE_LIMIT = 5


@dataclass
class Finding:
    check: str
    count: int
    summary: str
    samples: list = field(default_factory=list)


def _sample(rows) -> list:
    return [list(row) for row in list(rows)[:_SAMPLE_LIMIT]]


def find_stock_drift(cur) -> Finding | None:
    """A product's aggregate stock must equal the sum of its batches."""
    cur.execute(
        "SELECT p.id, p.product_name, p.stock_quantity, COALESCE(SUM(b.quantity), 0) AS batch_total "
        "FROM Products p LEFT JOIN Batch b ON b.product_id = p.id "
        "GROUP BY p.id HAVING p.stock_quantity <> COALESCE(SUM(b.quantity), 0)"
    )
    rows = cur.fetchall()
    if not rows:
        return None
    return Finding(
        check="stock_total_vs_batches",
        count=len(rows),
        summary="product stock does not match the sum of its batches",
        samples=_sample(rows),
    )


def find_sale_arithmetic_drift(cur) -> Finding | None:
    """Saved sale facts must stay internally consistent.

    Sale lines are only compared when the historical line value exists, so a
    receipt rebuilt from an older sale is not reported as damage.
    """
    cur.execute(
        "SELECT pu.id, pu.total_price, pu.discount_amount, COALESCE(SUM(sd.line_subtotal), 0) AS line_total, "
        "pu.price_with_tax, COALESCE(pu.total_tax, 0) AS tax "
        "FROM Purchase pu LEFT JOIN Sales_details sd ON sd.purchase_id = pu.id "
        "WHERE EXISTS (SELECT 1 FROM Sales_details s2 "
        "              WHERE s2.purchase_id = pu.id AND s2.line_subtotal IS NOT NULL) "
        "GROUP BY pu.id "
        "HAVING ABS(COALESCE(SUM(sd.line_subtotal), 0) - (pu.total_price + pu.discount_amount)) > %s "
        "   OR ABS(pu.total_price + COALESCE(pu.total_tax, 0) - pu.price_with_tax) > %s",
        (TOLERANCE, TOLERANCE),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    return Finding(
        check="sale_line_and_tax_arithmetic",
        count=len(rows),
        summary="a saved sale's line values, discount or tax no longer add up",
        samples=_sample(rows),
    )


def find_credit_ledger_drift(cur) -> Finding | None:
    """A credit row may never be negative, and may not exceed the sale it came from."""
    cur.execute(
        "SELECT k.id, k.customer_id, k.amount_paid, k.amount_due, pu.id, pu.price_with_tax "
        "FROM Customer_Khatoo k JOIN Purchase pu ON pu.id = k.purchase_id "
        "WHERE k.amount_paid < -%s OR k.amount_due < -%s "
        "   OR (k.amount_paid + k.amount_due) > pu.price_with_tax + %s",
        (TOLERANCE, TOLERANCE, TOLERANCE),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    return Finding(
        check="customer_credit_ledger",
        count=len(rows),
        summary="a customer balance is negative or larger than the sale that created it",
        samples=_sample(rows),
    )


def find_excess_refunds(cur) -> Finding | None:
    """Refunds against one sale can never exceed what was charged for it."""
    cur.execute(
        "SELECT cr.purchase_id, ROUND(SUM(cr.refund_amount), 2) AS refunded, pu.price_with_tax "
        "FROM Customer_Returns cr JOIN Purchase pu ON pu.id = cr.purchase_id "
        "GROUP BY cr.purchase_id HAVING SUM(cr.refund_amount) > pu.price_with_tax + %s",
        (TOLERANCE,),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    return Finding(
        check="refunds_within_sale_value",
        count=len(rows),
        summary="a sale has been refunded for more than it was charged",
        samples=_sample(rows),
    )


def find_shift_drift(cur) -> Finding | None:
    """A closed shift's stored cash expectation must match the current rows.

    This re-derives the same rule the drawer uses (opening float plus cash sales
    plus cash credit collections plus cash in, less cash out and refunds) from the
    rows as they are now. It catches a payment, sale or movement that changed
    after the shift was closed, or a restore that lost some of them.
    """
    cur.execute(
        "SELECT s.id, s.expected_cash_system, s.closing_cash_actual, s.cash_discrepancy, "
        "ROUND(s.opening_cash "
        " + COALESCE((SELECT SUM(p.price_with_tax) FROM Purchase p WHERE p.session_id = s.id AND p.payment_method = 'Cash'), 0) "
        " + COALESCE((SELECT SUM(cp.amount) FROM Credit_Payment cp WHERE cp.session_id = s.id AND cp.payment_method = 'Cash'), 0) "
        " + COALESCE((SELECT SUM(m.amount) FROM Cash_Movement m WHERE m.session_id = s.id AND m.movement_type = 'CASH_IN'), 0) "
        " - COALESCE((SELECT SUM(m.amount) FROM Cash_Movement m WHERE m.session_id = s.id AND m.movement_type = 'CASH_OUT'), 0) "
        " - COALESCE((SELECT SUM(m.amount) FROM Cash_Movement m WHERE m.session_id = s.id AND m.movement_type = 'REFUND'), 0), 2) AS expected "
        "FROM Cash_Register_Session s WHERE s.status = 'CLOSED'"
    )
    rows = cur.fetchall()
    drifted = [
        row
        for row in rows
        if abs(float(row[4] or 0) - float(row[1] or 0)) > TOLERANCE
        or abs((float(row[2] or 0) - float(row[4] or 0)) - float(row[3] or 0)) > TOLERANCE
    ]
    if not drifted:
        return None
    return Finding(
        check="closed_shift_cash_reconciliation",
        count=len(drifted),
        summary="a closed shift's counted cash no longer reconciles with its sales and movements",
        samples=_sample(drifted),
    )


def find_orphan_rows(cur) -> Finding | None:
    """Rows whose parent is gone indicate a partial restore or manual edit."""
    cur.execute(
        "SELECT 'credit row without its sale', COUNT(*) FROM Customer_Khatoo k "
        "  LEFT JOIN Purchase pu ON pu.id = k.purchase_id WHERE pu.id IS NULL "
        "UNION ALL "
        "SELECT 'sale line without its sale', COUNT(*) FROM Sales_details sd "
        "  LEFT JOIN Purchase pu ON pu.id = sd.purchase_id WHERE pu.id IS NULL "
        "UNION ALL "
        "SELECT 'batch without its product', COUNT(*) FROM Batch b "
        "  LEFT JOIN Products p ON p.id = b.product_id WHERE p.id IS NULL "
        "UNION ALL "
        "SELECT 'repayment without its credit row', COUNT(*) FROM Credit_Payment cp "
        "  LEFT JOIN Customer_Khatoo k ON k.id = cp.khatoo_id WHERE k.id IS NULL"
    )
    rows = [row for row in cur.fetchall() if int(row[1] or 0) > 0]
    if not rows:
        return None
    return Finding(
        check="orphan_rows",
        count=sum(int(row[1]) for row in rows),
        summary="records whose parent record is missing",
        samples=[[row[0], int(row[1])] for row in rows],
    )


_CHECKS = (
    find_stock_drift,
    find_sale_arithmetic_drift,
    find_credit_ledger_drift,
    find_excess_refunds,
    find_shift_drift,
    find_orphan_rows,
)


def reconcile() -> dict:
    """Run every identity check against the local shop database."""
    findings: list[Finding] = []
    with get_db() as (_conn, cur):
        for check in _CHECKS:
            try:
                found = check(cur)
            except Exception as exc:
                # Evaluated-and-failed has to be visible: an unavailable check is
                # reported, never silently treated as a healthy shop.
                logger.error("Reconciliation check %s could not run: %s", check.__name__, exc)
                findings.append(
                    Finding(check=check.__name__, count=0, summary=f"could not be evaluated: {exc}")
                )
                continue
            if found:
                findings.append(found)

    for finding in findings:
        logger.warning("Reconciliation finding %s: %s", finding.check, finding.summary)

    return {
        "ok": not findings,
        "findings": [asdict(finding) for finding in findings],
        "finding_count": sum(finding.count for finding in findings),
        "checks_run": len(_CHECKS),
        "tolerance": TOLERANCE,
        "checked_at": business_now().isoformat(timespec="seconds"),
    }


def format_findings(report: dict) -> str:
    """Plain-language summary for an operator or a support bundle."""
    if report.get("ok"):
        return "No accounting drift found."
    lines = ["Accounting drift found in the shop data:"]
    for finding in report.get("findings", []):
        lines.append(f"- {finding['summary']} ({finding['count']} record(s))")
    lines.append("Restore a verified recent backup and contact support before trusting these totals.")
    return "\n".join(lines)
