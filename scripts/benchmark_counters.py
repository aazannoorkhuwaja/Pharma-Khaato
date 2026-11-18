"""Disposable local service benchmark. Never opens a configured live store."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time


def run(products=1000, operations=200, counters=4):
    if not (1 <= products <= 100000 and 1 <= operations <= 10000 and 1 <= counters <= 32):
        raise ValueError('Benchmark sizes are outside supported limits.')
    root=Path(tempfile.mkdtemp(prefix='pharma-counter-benchmark-'))
    os.environ['PHARMA_KHAATO_DATA_DIR']=str(root)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from core.path_manager import PathManager
    if PathManager._BASE_DATA_DIR is not None:
        raise RuntimeError('Run this benchmark in a fresh process.')
    from core.db_engine import get_db,reset_thread_connections
    from core.auth_service import register_initial_admin
    from core.product_search_service import search_sellable_products
    from core.pos_service import CheckoutRequest,POSTransactionEngine
    from core.financial_storage import storage_reconciliation
    assert register_initial_admin('benchmark-owner','benchmark-password','Fixture','Owner')[0]
    with get_db(immediate=True) as (_,cur):
        cur.execute("INSERT INTO Supplier(supplier_name,supplier_company_name,Email_address,phone_number) VALUES('Fixture','Fixture','none@example.invalid','0')")
        for index in range(products):
            cur.execute("INSERT INTO Products(product_name,company_name,category,price,stock_quantity) VALUES(%s,'Fixture','Fixture',.10,%s)",(f'Benchmark Medicine {index}',operations+1))
            cur.execute("INSERT INTO Batch(number_of_product,expiry_date,product_id,supplier_id,quantity,manufacture_Date) VALUES('FIXTURE','2099-12-31',%s,1,%s,'2026-01-01')",(index+1,operations+1))
    def counter(index):
        started=time.perf_counter()
        try:
            search_sellable_products(f'Benchmark Medicine {index % products}')
            result=POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',1,[{'prod_id':index%products+1,'qty':1,'price':.10}],payment_method='Card',checkout_token=f'benchmark-{index}',terminal_id=f'counter-{index%counters}'))
            if not result.success:raise AssertionError(result.message)
            return (time.perf_counter()-started)*1000
        finally:reset_thread_connections()
    started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=counters) as pool:latencies=list(pool.map(counter,range(operations)))
    duration=time.perf_counter()-started
    with get_db() as (conn,cur):
        cur.execute('SELECT COUNT(*),SUM(price_with_tax_minor) FROM Purchase')
        count,total=cur.fetchone()
        assert (count,total)==(operations,operations*10)
        integrity=storage_reconciliation(conn.raw_conn)
        assert integrity['ok']
    values=sorted(latencies)
    return {'mode':'local authoritative services; excludes TLS and real network latency','products':products,'operations':operations,'counters':counters,'seconds':duration,'p50_ms':statistics.median(values),'p95_ms':values[min(len(values)-1,int(len(values)*.95))],'max_ms':max(values),'sale_count':count,'sales_minor':total,'integer_reconciliation':integrity['ok'],'isolated_directory':str(root)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--products',type=int,default=1000)
    parser.add_argument('--operations',type=int,default=200)
    parser.add_argument('--counters',type=int,default=4)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run(args.products,args.operations,args.counters)
    with args.output.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2)
    print(json.dumps(result,indent=2))
