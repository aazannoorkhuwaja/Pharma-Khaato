# Edge-case test matrix and reproduction evidence

Audit evidence collected: 2026-11-10; reports finalized: 2026-11-11. Phase 1: analysis and documentation only.

Baseline: local `ui/reference-replica`, commit `1dd242cebae3ca792750fc8dc91f03b84a7705ec`, matching the GitHub branch at inspection. GitHub `main` was `1fc56654c5a69ae62525a13b17c6235568f6eee6`; findings target the audited branch, not an assertion that main has identical UI. No application code, live database, merge, deployment, or release changes were made.

Evidence labels: **Reproduced** = observed in a disposable database or recorded exact-commit CI; **Source-confirmed** = reachable behavior established by code inspection; **Risk** = plausible consequence requiring a targeted experiment; **Unverified** = missing acceptance evidence. Severity reflects business impact, not exploitability alone. Complexity: S = 1–2 engineering days; M = 3–5; L = 1–2 weeks; XL = multiple weeks. Estimates exclude independent acceptance, regulatory review and rollout; overlapping fixes must not simply be summed.

## Executed evidence

Local command (temporary application data and pytest cache):

```bash
PYTHONDONTWRITEBYTECODE=1 PHARMA_KHAATO_DATA_DIR=/tmp/pharma-phase1-suite QT_QPA_PLATFORM=offscreen python3 -m pytest -q -o cache_dir=/tmp/pharma-phase1-pytest-cache
```

Result: **284 passed, 44 errors, 112.80 seconds**. Thirty-two setup errors were missing `qapp`/`qtbot` fixtures (pytest-qt unavailable); twelve were socket permission errors in the execution sandbox. This is an incomplete suite, not a passing full run. Runtime: Python 3.14.4, PySide6-Essentials/shiboken6 6.12.0, cryptography 46.0.5, python-dotenv 1.2.4, pytest 9.0.2. This differs from the pinned Python 3.12/Qt 6.7.2 release environment. No numerical line/branch coverage was collected; test counts are not coverage percentages.

Exact-commit remote evidence: [CI](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/42718526490) failed all four jobs. Inspected Ubuntu and Windows Python 3.12 logs each report **327 passed, 1 failed**, with the checkout total-placement assertion failing. [UI acceptance](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/42718526309) passed Ubuntu and failed Windows at all three scale factors. The inspected Windows 1.5 job reports three clipped-shortcut cases. Local fixture failures therefore must not be used to dismiss the actual remote layout defects.

## Required regression matrix

Status is audit evidence, not a statement that all listed future assertions are already implemented. P0 gates financial integrity, medicine safety and recovery; P1 gates safe LAN operation and usability; P2 gates scale and sustained support.

| ID / priority | Scenario and required invariant | Evidence now | Test layer / owner |
|---|---|---|---|
| A01 / P0 | Two counters, same employee; every cash refund belongs to the trusted requesting terminal shift | Wrong shift reproduced | Service + LAN integration / backend |
| A02 / P0 | Product-price changes cannot sell any allocated unit above configured batch MRP | Bypass reproduced | Transaction + GUI / pharmacy domain |
| A03 / P0 | All sold quantities remain returnable under policy even after monetary refund reaches zero; cumulative payout never exceeds entitlement | Partial/zero return failures reproduced | Property-based + ledger / domain |
| A04 / P0 | Lost reply after commit preserves operation ID and resolves to exactly one posting after restart | Pending identity loss reproduced; duplicate not reproduced | Fault injection + subprocess / backend |
| A05 / P0 | Prescription flag follows defined clinical authorization policy, including crafted remote requests | Missing enforcement source-confirmed | Policy + integration / clinical owner |
| D01 / P0 | Restore rejects incomplete/foreign/newer schema before replacing live target; old data recoverable after all failures | Missing-table restore accepted | Disposable file lifecycle / database |
| D02 / P0 | Invalid/expired/quarantined lots never allocate; valid FEFO order deterministic | Malformed expiry accepted | Property + migration / domain |
| D03 / P0 | Sale, tender, tax, discount, refund and credit ledger reconcile exactly at documented precision | Representation risk | Decimal reference + migration / database |
| D04 / P0 | All supported upgrades are atomic; schema drift/downgrade refused safely | Inspection only | Version fixtures + power interruption / database |
| D05 / P0 | One maintenance owner across GUI/CLI/processes; no writes to obsolete restored file | Unexecuted | Linux/Windows subprocess / platform |
| CASH / P0 | Concurrent checkout/refund/close never posts to closed shift; expected balance equals counted components | Requires dedicated race proof | Barrier-synchronized workers / backend |
| CREDIT / P0 | Concurrent payments/returns cannot over-repay, erase debt incorrectly, or refund twice | Requires reconciliation experiments | Service + restart / backend |
| STOCK / P0 | Two counters competing for last unit produce one sale; each stock delta has one movement; transaction failures leave no partial state | Existing tests not equivalent to full multi-process proof | Subprocess + invariant / database |
| UNITS / P0 | Box/strip/base conversion preserves exact base quantities and historical meaning after catalog edits | Acceptance gap | Property + legacy fixtures / domain |
| SUPPLIER / P0 | Duplicate receipt/payment and returns reconcile stock and supplier balance with one durable operation | Acceptance gap | Ledger + fault injection / backend |
| S01 / P1 | Slow handshake/headers/body cannot starve valid counters; thread/memory growth bounded | Network tests blocked locally | Isolated network load / security |
| S02 / P1 | Login spraying/session abandonment bounded; legitimate lockout/revocation preserved | Retention risk | Capacity + clock control / security |
| S03 / P0 | Crafted backup cannot supply its own recovery authority under the agreed shared-counter threat model | Trust decision confirmed | Disposable recovery / security |
| S04 / P1 | Other OS users cannot read DB/WAL/backups/receipts under supported install defaults | ACLs unverified | Clean Windows/Linux install / release |
| S05 / P1 | CSV strings remain inert in supported spreadsheet clients | Unsafe export confirmed | Export + manual spreadsheet / QA |
| S06 / P1 | Exact shipped binaries have SBOM, advisory decisions and reproducible dependency inventory | Full scan not performed | Artifact scan / release |
| AUTH / P0 | Every mutation enforces actor role and trusted terminal; reset/deactivation revokes existing authority as specified | Partial source review | Local/LAN permission matrix / security |
| U01–U02 / P1 | Total/change/checkout remain visible; labels/shortcuts fit all supported DPI/window scenarios | Remote CI failures | pytest-qt + screenshots / frontend |
| U03 / P1 | GUI remains responsive during timeout; no duplicate save or late stale result | Synchronous calls confirmed | Delayed fake transport / frontend |
| U04 / P0 | Confirmed refund quote equals committed refund, or requires explicit reconfirmation on changed state | 0.66 versus 0.67 reproduced | Shared quote + GUI / domain |
| U05 / P1 | Mixed-price lots have a comprehensible, safe sale flow | Workflow gap | End-to-end cashier acceptance / frontend |
| U06 / P0 | Failed expiry/reorder query displays unavailable/stale state, never false zero | Exception masking confirmed | Fault injection + GUI / frontend |
| U07 / P1 | Keyboard and screen-reader operators can sell, return, reconcile and recover focus | Manual acceptance unexecuted | NVDA/Orca + OS themes / accessibility QA |
| U08 / P2 | Retained worker module imports and delivers success/error safely | Import failure reproduced | Import + lifetime / frontend |
| RECOVERY / P0 | New-host restore recovers data, trust, operation identity and receipts within RPO/RTO | DB-only scope gap | Full drill / operations |
| RELEASE / P1 | Install/update/uninstall/rollback preserve data and permission policy on clean supported systems | No artifact acceptance executed here | Signed packages + VM matrix / release |
| HARDWARE / P1 | Scanner timing, printer failures, paper widths, offline printing and reprint do not duplicate sales | Unverified | Physical devices / QA |
| SOAK / P2 | Day-long multi-counter load, large catalogs and backup retention remain bounded | Unexecuted | Performance + fault soak / QA |

## Reproduction safety and interpretation

The following audit probe creates a new temporary data directory **before importing application modules**. It intentionally corrupts and restores only that disposable store. Run in a disposable checkout/profile, never adapt it to a live shop path. It demonstrates current defects and prints outcomes; it is not a permanent regression suite or a production repair script. Replace the checkout path if necessary. The known scratch credentials below belong solely to the newly created fixture.

```python
import os,sys,tempfile,json,sqlite3
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='pharma-audit-probe-'))
os.environ['PHARMA_KHAATO_DATA_DIR']=str(root)
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,'/home/aazan-noor-khuwaja/Projects/Pharma-Khaato')
from core import db_engine as db
from core.auth_service import register_initial_admin
assert register_initial_admin('auditadmin','auditpass123','Audit','Admin')[0]
with db.get_db(immediate=True) as (_,c):
 c.execute("INSERT INTO Supplier(supplier_name,supplier_company_name,Email_address,phone_number) VALUES('Audit supplier','Audit','test@example.invalid','0300')")
 c.execute("INSERT INTO Products(product_name,company_name,category,barcode,stock_quantity,price) VALUES('Audit med','Audit','General','AUDIT',100,15)")
 c.execute("INSERT INTO Batch(product_id,number_of_product,quantity,expiry_date,manufacture_Date,supplier_id) VALUES(1,'AUDIT',100,'2099-12-31','2020-01-01',1)")
from core.cash_session_service import open_session
from core.pos_service import CheckoutRequest,POSTransactionEngine
from core.lan_service import ShopService
sa=open_session(1,100,terminal_id='A')[1];sb=open_session(1,100,terminal_id='B')[1]
sale=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':1,'qty':1,'price':15}],terminal_id='A',checkout_token='audit-sale-A'))
assert sale.success,sale
svc=ShopService();token=svc.login('auditadmin','auditpass123','A')['token']
ret=svc.call(token,'ReturnModel','process',args=[sale.purchase_id,[{'batch_id':1,'qty':1}],1,'Audit return','SELLABLE'],kwargs={'operation_id':'audit-return-A'},request_id='audit-request-A')
with db.get_db() as (_,c):
 c.execute('SELECT session_id FROM Customer_Returns WHERE purchase_id=%s',(sale.purchase_id,));actual=c.fetchone()[0]
print('REFUND_WRONG_COUNTER',json.dumps({'return_success':ret[0],'expected_A':sa,'actual':actual,'B':sb}))
from core.inventory_service import register_product,add_batch,update_product
assert register_product('MRP audit',10)[0]
assert add_batch(2,1,10,'2099-12-31',mrp=10)[0]
assert update_product(2,name='MRP audit',price=20,employee_id=1)[0]
s=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':2,'qty':1,'price':20}],payment_method='Card',checkout_token='mrp-sale'))
print('MRP_BYPASS',json.dumps({'sale_success':s.success,'total':s.total,'message':s.message}))
from core.manager_auth_service import issue_discount_approval
from core.return_service import process_return
assert register_product('Rounding audit',.01)[0]
assert add_batch(3,1,10,'2099-12-31')[0]
approval=issue_discount_approval('auditadmin','auditpass123',1,.01,.03)[0]
s=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':3,'qty':3,'price':.01}],discount=.01,payment_method='Card',checkout_token='round-sale',manager_approval_token=approval))
assert s.success,s
out=[process_return(s.purchase_id,[{'batch_id':3,'qty':1}],1,'Audit rounding','SELLABLE',f'round-{i}') for i in range(3)]
print('ROUNDING_RETURN',json.dumps(out))
approval=issue_discount_approval('auditadmin','auditpass123',1,.01,.01)[0]
s=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':3,'qty':1,'price':.01}],discount=.01,payment_method='Card',checkout_token='zero-sale',manager_approval_token=approval))
print('ZERO_VALUE_RETURN',json.dumps({'sale_success':s.success,'return':process_return(s.purchase_id,[{'batch_id':3,'qty':1}],1,'Audit zero','SELLABLE','zero-return')}))
from core.local_operations import perform,pending
result=perform(1,'movement',{'amount':1},lambda operation:(False,'Cash shift result could not be confirmed. Refresh its status before trying again.'))
print('PENDING_UNKNOWN_CLEARED',json.dumps({'result':result,'pending':pending(1)}))
from core.path_manager import PathManager
from core.backup_service import _validate_sqlite_database
path=root/'audit-missing-table.sqlite'
with sqlite3.connect(path) as copy:
 db.get_conn().raw_conn.backup(copy)
 copy.execute('DROP TABLE Return_Operation');copy.commit()
print('INCOMPLETE_BACKUP_ACCEPTED',json.dumps(_validate_sqlite_database(str(path))))
print('ISOLATED_DATA',str(root))
# New audit-only scenarios, still in the disposable store above.
assert register_product('Pack precision audit',1,units_per_box=3)[0]
assert update_product(4,name='Pack precision audit',price=.3333,units_per_box=3,employee_id=1)[0]
assert add_batch(4,1,9,'2099-12-31')[0]
s=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':4,'qty':1,'price':1,'unit_code':'box','unit_multiplier':3}],payment_method='Card',checkout_token='pack-sale'))
assert s.success,s
from core.return_service import get_returnable_sale
from ui.screens.returns_screen import ReturnsScreen
from types import SimpleNamespace
preview=ReturnsScreen._preview_refund(SimpleNamespace(current_sale=get_returnable_sale(s.purchase_id)),{4:2})
actual=process_return(s.purchase_id,[{'batch_id':4,'qty':2}],1,'Audit pack','SELLABLE','pack-return')
print('PREVIEW_MISMATCH',json.dumps({'preview':str(preview),'actual':actual[1]['refund_amount']}))
with db.get_db(immediate=True) as (_,c):
 c.execute("UPDATE Batch SET expiry_date='not-a-date' WHERE id=4")
s=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':4,'qty':1,'price':.33}],payment_method='Card',checkout_token='invalid-expiry-sale'))
print('INVALID_LEGACY_EXPIRY',json.dumps({'success':s.success,'message':s.message}))
try:
 import ui.app.state.async_worker
except ImportError as e:
 print('DORMANT_WORKER_IMPORT',str(e))
from core.backup_service import restore_database
print('INCOMPLETE_RESTORE',json.dumps(restore_database(str(path))))
with db.get_db() as (_,c):
 c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='Return_Operation'")
 print('RESTORED_RETURN_OPERATION_TABLE_COUNT',c.fetchone()[0])

```

Observed output:

```text
2026-11-10 11:19:37,748 [INFO] Creating fresh SQLite embedded database at: /tmp/pharma-audit-probe-5euqbi73/data/pharmacy_db.sqlite
2026-11-10 11:19:37,751 [INFO] SQLite schema initialized successfully.
2026-11-10 11:19:37,751 [INFO] Applying database migration script: 001_initial_schema.sql
2026-11-10 11:19:37,752 [INFO] Successfully applied migration: 001_initial_schema.sql
2026-11-10 11:19:37,752 [INFO] Applying database migration script: 002_add_indexes.sql
2026-11-10 11:19:37,752 [INFO] Successfully applied migration: 002_add_indexes.sql
2026-11-10 11:19:37,752 [INFO] Applying database migration script: 003_industry_level_features.sql
2026-11-10 11:19:37,752 [INFO] Successfully applied migration: 003_industry_level_features.sql
2026-11-10 11:19:37,752 [INFO] Applying database migration script: 004_formal_data_architecture.sql
2026-11-10 11:19:37,753 [INFO] Successfully applied migration: 004_formal_data_architecture.sql
2026-11-10 11:19:37,753 [INFO] Applying database migration script: 005_cash_register_sessions.sql
2026-11-10 11:19:37,753 [INFO] Successfully applied migration: 005_cash_register_sessions.sql
2026-11-10 11:19:37,753 [INFO] Applying database migration script: 006_cash_movements.sql
2026-11-10 11:19:37,754 [INFO] Successfully applied migration: 006_cash_movements.sql
2026-11-10 11:19:37,754 [INFO] Applying database migration script: 007_customer_returns.sql
2026-11-10 11:19:37,754 [INFO] Successfully applied migration: 007_customer_returns.sql
2026-11-10 11:19:37,754 [INFO] Applying database migration script: 008_fts5_catalog.sql
2026-11-10 11:19:37,755 [INFO] Successfully applied migration: 008_fts5_catalog.sql
2026-11-10 11:19:37,755 [INFO] Applying database migration script: 009_login_lockout.sql
2026-11-10 11:19:37,755 [INFO] Successfully applied migration: 009_login_lockout.sql
2026-11-10 11:19:37,755 [INFO] Applying database migration script: 010_normalize_cnic.sql
2026-11-10 11:19:37,756 [INFO] Successfully applied migration: 010_normalize_cnic.sql
2026-11-10 11:19:37,756 [INFO] Applying database migration script: 011_normalize_dates.sql
2026-11-10 11:19:37,756 [INFO] Successfully applied migration: 011_normalize_dates.sql
2026-11-10 11:19:37,756 [INFO] Applying database migration script: 012_credit_payments_and_perf.sql
2026-11-10 11:19:37,757 [INFO] Successfully applied migration: 012_credit_payments_and_perf.sql
2026-11-10 11:19:37,757 [INFO] Applying database migration script: 013_returns_holds_hardening.sql
2026-11-10 11:19:37,761 [INFO] Successfully applied migration: 013_returns_holds_hardening.sql
2026-11-10 11:19:37,761 [INFO] Applying database migration script: 014_receipt_templates.sql
2026-11-10 11:19:37,761 [INFO] Successfully applied migration: 014_receipt_templates.sql
2026-11-10 11:19:37,761 [INFO] Applying database migration script: 015_ui_performance_indexes.sql
2026-11-10 11:19:37,762 [INFO] Successfully applied migration: 015_ui_performance_indexes.sql
2026-11-10 11:19:37,762 [INFO] Applying database migration script: 016_checkout_idempotency.sql
2026-11-10 11:19:37,763 [INFO] Successfully applied migration: 016_checkout_idempotency.sql
2026-11-10 11:19:37,763 [INFO] Applying database migration script: 017_checkout_request_lifecycle.sql
2026-11-10 11:19:37,763 [INFO] Successfully applied migration: 017_checkout_request_lifecycle.sql
2026-11-10 11:19:37,763 [INFO] Applying database migration script: 018_financial_integrity.sql
2026-11-10 11:19:37,770 [INFO] Successfully applied migration: 018_financial_integrity.sql
2026-11-10 11:19:37,770 [INFO] Applying database migration script: 019_pharmacy_units.sql
2026-11-10 11:19:37,777 [INFO] Successfully applied migration: 019_pharmacy_units.sql
2026-11-10 11:19:37,777 [INFO] Applying database migration script: 020_simple_customer_credit.sql
2026-11-10 11:19:37,780 [INFO] Successfully applied migration: 020_simple_customer_credit.sql
2026-11-10 11:19:37,781 [INFO] Applying database migration script: 021_manager_approvals.sql
2026-11-10 11:19:37,781 [INFO] Successfully applied migration: 021_manager_approvals.sql
2026-11-10 11:19:37,781 [INFO] Applying database migration script: 022_receipt_snapshots.sql
2026-11-10 11:19:37,781 [INFO] Successfully applied migration: 022_receipt_snapshots.sql
2026-11-10 11:19:37,781 [INFO] Applying database migration script: 023_lan_sessions.sql
2026-11-10 11:19:37,782 [INFO] Successfully applied migration: 023_lan_sessions.sql
2026-11-10 11:19:37,782 [INFO] Applying database migration script: 024_return_operations.sql
2026-11-10 11:19:37,782 [INFO] Successfully applied migration: 024_return_operations.sql
2026-11-10 11:19:37,782 [INFO] Applying database migration script: 025_supplier_accounts.sql
2026-11-10 11:19:37,783 [INFO] Successfully applied migration: 025_supplier_accounts.sql
2026-11-10 11:19:39,282 [INFO] Database restored; previous files preserved in /tmp/pharma-audit-probe-5euqbi73/backups/before_restore_20261110_111939_279892
REFUND_WRONG_COUNTER {"return_success": true, "expected_A": 1, "actual": 2, "B": 2}
MRP_BYPASS {"sale_success": true, "total": 20.0, "message": "Sale #2 completed."}
ROUNDING_RETURN [[true, {"return_id": 2, "purchase_id": 3, "refund_amount": 0.01, "refund_tenders": [["Credit Card", 0.01]], "items": 1}], [true, {"return_id": 3, "purchase_id": 3, "refund_amount": 0.01, "refund_tenders": [["Credit Card", 0.01]], "items": 1}], [false, "This sale has already been fully refunded."]]
ZERO_VALUE_RETURN {"sale_success": true, "return": [false, "This sale has already been fully refunded."]}
PENDING_UNKNOWN_CLEARED {"result": [false, "Cash shift result could not be confirmed. Refresh its status before trying again."], "pending": null}
INCOMPLETE_BACKUP_ACCEPTED [true, "ok"]
ISOLATED_DATA /tmp/pharma-audit-probe-5euqbi73
PREVIEW_MISMATCH {"preview": "0.66", "actual": 0.67}
INVALID_LEGACY_EXPIRY {"success": true, "message": "Sale #6 completed."}
DORMANT_WORKER_IMPORT cannot import name 'Runnable' from 'PySide6.QtCore' (/home/aazan-noor-khuwaja/.local/lib/python3.14/site-packages/PySide6/QtCore.abi3.so)
INCOMPLETE_RESTORE [true, "Backup restored successfully. Previous data was preserved. Restart the application."]
RESTORED_RETURN_OPERATION_TABLE_COUNT 0

```

## QA execution strategy

Convert each reproduced defect into an assertion against the desired invariant before implementing its fix. Use fresh stores and representative migrated fixtures; never production databases. Separate deterministic unit/property tests, transactional integration tests, process/network fault tests, Qt interaction tests, visual geometry checks and manual hardware/assistive-technology acceptance. Test Linux and Windows against exact release dependencies.

Record seeds, barrier synchronization, monotonic deadlines, OS/Python/Qt versions and artifacts. Avoid sleep-based races and retrying failing tests until green. A single failed CI run does not establish flakiness; repeated controlled runs are needed to classify a flaky test. Gate release on invariant reconciliation, recovery drills, authorization tests and cashier acceptance in addition to green CI.
