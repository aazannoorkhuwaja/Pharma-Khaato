import sys
import os
from datetime import date

# Add the project directory to sys.path so we can import our functions
sys.path.append('/home/aazan-noor-khuwaja/Aazan_ Data/4th_Semester/Database-Learning/DB-Project/project')

from salesman_app import (
    db_get_low_stock, 
    db_get_khatoo_summary, 
    db_add_batch, 
    db_get_all_products, 
    db_get_suppliers
)

def run_test():
    print("🚀 Starting Backend Verification...")
    
    # 1. Test Dashboard Stats
    print("\n[1/3] Testing Dashboard Summary...")
    debt = db_get_khatoo_summary()
    print(f"✅ Total Debt retrieved: Rs. {debt:,.2f}")
    
    low_stock = db_get_low_stock()
    print(f"✅ Low Stock items found: {len(low_stock)}")
    for item in low_stock:
        print(f"   - Alert: {item[0]} is at {item[1]} (Min: {item[2]})")

    # 2. Test Product/Supplier Fetch
    print("\n[2/3] Testing Data Lookups...")
    prods = db_get_all_products()
    supps = db_get_suppliers()
    if prods and supps:
        print(f"✅ Successfully found {len(prods)} products and {len(supps)} suppliers.")
    else:
        print("❌ Data lookup failed or tables are empty.")
        return

    # 3. Test Stock Addition (The Technician Role)
    print("\n[3/3] Testing Stock Addition (Technician Role)...")
    p_id = prods[0][0]
    s_id = supps[0][0]
    qty = 50
    expiry = "2029-01-01"
    mfg = date.today().strftime("%Y-%m-%d")
    
    print(f"⏳ Attempting to add {qty} units to Product ID {p_id}...")
    ok = db_add_batch(p_id, s_id, qty, expiry, mfg)
    
    if ok:
        print("✅ Stock added successfully! (Backend verified)")
    else:
        print("❌ Stock addition failed!")

if __name__ == "__main__":
    run_test()
