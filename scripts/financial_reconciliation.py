"""Read-only reconciliation for a copied pharmacy database; never repairs it."""
from __future__ import annotations
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.financial_storage import storage_reconciliation


def reconcile(path):
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        result = storage_reconciliation(conn)
        integrity = conn.execute('PRAGMA quick_check').fetchall()
        if integrity != [('ok',)]:
            result['issues'].append({'problem':'sqlite_integrity_check_failed'})
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            result['issues'].append({'problem':'foreign_key_check_failed'})
        if any(row['problem'] in {'missing_integer_column','missing_table'} for row in result['issues']):
            result.update(ok=False, review_required=True, legacy_rounding=[],
                          next_step='Review historical amounts, then migrate a disposable copy using the matching application before full ledger reconciliation.')
            return result
        for product, stock, batches in conn.execute('SELECT p.id,p.stock_quantity,COALESCE(SUM(b.quantity),0) FROM Products p LEFT JOIN Batch b ON b.product_id=p.id GROUP BY p.id HAVING p.stock_quantity != COALESCE(SUM(b.quantity),0)'):
            result['issues'].append({'problem':'stock_total_mismatch','product_id':product,'product_stock':stock,'batch_stock':batches})
        for purchase, gross, returned in conn.execute('SELECT p.id,p.price_with_tax_minor,COALESCE(SUM(r.refund_amount_minor),0) FROM Purchase p LEFT JOIN Customer_Returns r ON r.purchase_id=p.id GROUP BY p.id HAVING COALESCE(SUM(r.refund_amount_minor),0)>p.price_with_tax_minor'):
            result['issues'].append({'problem':'refund_exceeds_sale','purchase_id':purchase,'gross_minor':gross,'refund_minor':returned})
        for purchase,batch,sold,returned in conn.execute('SELECT sd.purchase_id,sd.batch_id,sd.Quantity,COALESCE((SELECT SUM(ri.quantity) FROM Return_Items ri JOIN Customer_Returns r ON r.id=ri.return_id WHERE r.purchase_id=sd.purchase_id AND ri.batch_id=sd.batch_id),0) AS returned FROM Sales_details sd WHERE returned>sd.Quantity'):
            result['issues'].append({'problem':'returned_quantity_exceeds_sale','purchase_id':purchase,'batch_id':batch})
        for row in conn.execute('SELECT id,amount_due_minor,amount_paid_minor FROM Customer_Khatoo WHERE amount_due_minor<0 OR amount_paid_minor<0'):
            result['issues'].append({'problem':'negative_credit_balance','ledger_id':row[0]})
        # Compare current debt + paid against original gross less returns. Do not
        # silently infer historical receipt amounts from current catalog prices.
        for ledger,purchase,account,entitlement in conn.execute('SELECT k.id,k.purchase_id,k.amount_due_minor+k.amount_paid_minor,p.price_with_tax_minor-COALESCE((SELECT SUM(refund_amount_minor) FROM Customer_Returns WHERE purchase_id=k.purchase_id),0) FROM Customer_Khatoo k JOIN Purchase p ON p.id=k.purchase_id WHERE k.amount_due_minor+k.amount_paid_minor != p.price_with_tax_minor-COALESCE((SELECT SUM(refund_amount_minor) FROM Customer_Returns WHERE purchase_id=k.purchase_id),0)'):
            result['issues'].append({'problem':'credit_sale_reconciliation','ledger_id':ledger,'purchase_id':purchase,'account_minor':account,'entitlement_minor':entitlement})
        for invoice, recorded, lines in conn.execute('SELECT i.id,i.total_minor,COALESCE(SUM(l.total_minor),0) FROM Supplier_Invoice i LEFT JOIN Supplier_Invoice_Line l ON l.invoice_id=i.id GROUP BY i.id HAVING i.total_minor != COALESCE(SUM(l.total_minor),0)'):
            result['issues'].append({'problem':'supplier_invoice_total_mismatch','invoice_id':invoice,'recorded_minor':recorded,'line_total_minor':lines})
        for line, received, returned, gross, credit in conn.execute('SELECT l.id,l.quantity,COALESCE(SUM(r.quantity),0),l.total_minor,COALESCE(SUM(r.credit_minor),0) FROM Supplier_Invoice_Line l LEFT JOIN Supplier_Return r ON r.invoice_line_id=l.id GROUP BY l.id HAVING COALESCE(SUM(r.quantity),0)>l.quantity OR COALESCE(SUM(r.credit_minor),0)>l.total_minor'):
            result['issues'].append({'problem':'supplier_return_exceeds_receipt','line_id':line})
        # Derive closed-shift expected cash from immutable tender and movement
        # facts. Non-cash sales/collections deliberately never enter this sum.
        for session, opening, expected, actual, discrepancy in conn.execute("SELECT id,opening_cash_minor,expected_cash_system_minor,closing_cash_actual_minor,cash_discrepancy_minor FROM Cash_Register_Session WHERE status='CLOSED'"):
            sales = conn.execute("SELECT COALESCE(SUM(price_with_tax_minor),0) FROM Purchase WHERE session_id=? AND payment_method='Cash'", (session,)).fetchone()[0]
            collections = conn.execute("SELECT COALESCE(SUM(amount_minor),0) FROM Credit_Payment WHERE session_id=? AND payment_method='Cash'", (session,)).fetchone()[0]
            movements = conn.execute("SELECT COALESCE(SUM(CASE WHEN movement_type='CASH_IN' THEN amount_minor ELSE -amount_minor END),0) FROM Cash_Movement WHERE session_id=?", (session,)).fetchone()[0]
            calculated = opening + sales + collections + movements
            if expected != calculated or actual is None or discrepancy != actual - calculated:
                result['issues'].append({'problem':'closed_cash_reconciliation','session_id':session,'calculated_minor':calculated,'recorded_minor':expected})
        result['ok'] = not result['issues']
        result['legacy_rounding'] = [dict(zip(('table','column','scale','rounded_rows'), row)) for row in conn.execute('SELECT table_name,column_name,scale,rounded_rows FROM Money_Migration_Evidence WHERE rounded_rows>0')]
        result['review_required'] = bool(result['legacy_rounding'])
        return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=reconcile(args.database)
    encoded=json.dumps(report,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8') as handle:handle.write(encoded)
    else:print(encoded)
    raise SystemExit(0 if report['ok'] and not report['review_required'] else 1)
