import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from core.auth_service import login_user, has_registered_employees, register_initial_admin
from core.customer_service import register_customer, search_customer, load_khatoo, record_payment
from core.inventory_service import search_products, get_near_expiry, get_expired_stock, clear_inventory_cache
from core.pos_service import confirm_sale, get_sales_history

def test_flow():
    print("=" * 60)
    print("  PHARMA-KHAATO SYSTEM INTEGRATION & END-TO-END SUITE  ")
    print("=" * 60)
    
    try:
        clear_inventory_cache()
        # Seed test admin if DB is fresh
        if not has_registered_employees():
            register_initial_admin("admin", "admin123", "Usman", "Admin")

        # 1. Authentication
        print("\n[1/6] Testing Employee Authentication...")
        user = login_user("admin", "admin123")
        assert user is not None, "Login failed for default admin user!"
        print(f"   ✓ Logged in as: {user[1]} ({user[3]})")

        # 2. Register Customer
        print("\n[2/6] Testing Customer Registration...")
        test_cnic = f"999{int(time.time())}"[:13]
        ok, msg = register_customer(test_cnic, "Integration", "Tester", "test@pharma.pk", "Peshawar")
        print(f"   ✓ Status: {msg}")

        # 3. Search Customer
        print("\n[3/6] Testing Customer Search...")
        custs = search_customer(test_cnic)
        assert len(custs) > 0, "Registered customer not found!"
        print(f"   ✓ Found: {custs[0][1]} {custs[0][2]} ({custs[0][0]})")

        # 4. Product & Stock Search
        print("\n[4/6] Testing FEFO Stock & Product Search...")
        prods = search_products("")
        if not prods:
            from scripts.seed_db import seed_database
            seed_database()
            clear_inventory_cache()
            prods = search_products("")
        assert len(prods) > 0, "No available products found in stock!"
        prod = prods[0]
        print(f"   ✓ Selected Item: {prod[1]} (Batch #{prod[3]}, Price: Rs.{prod[2]}, Stock: {prod[4]})")

        # 5. POS Checkout Transaction (Credit Khatoo)
        print("\n[5/6] Testing POS Checkout & Credit Ledger...")
        cart = [{
            "prod_id": prod[0],
            "name": prod[1],
            "price": float(prod[2]),
            "batch_id": prod[3],
            "qty": 2,
            "subtotal": float(prod[2]) * 2
        }]
        ok, msg = confirm_sale(test_cnic, user[0], cart, total=float(prod[2]) * 2, discount=0.0, payment_method="Credit (Khatoo)")
        assert ok, f"Checkout failed: {msg}"
        print(f"   ✓ Checkout Status: {msg}")

        # 6. Khatoo Payment Recording
        print("\n[6/6] Testing Khatoo Debt Settlement...")
        khatoo_data = load_khatoo(test_cnic)
        assert len(khatoo_data) > 0, "Khatoo credit record not generated after credit sale!"
        unpaid = [k for k in khatoo_data if float(k[3]) > 0]
        if unpaid:
            k_id = unpaid[0][0]
            due  = float(unpaid[0][3])
            pay_amt = round(min(10.0, due), 2)
            ok, pmsg = record_payment(k_id, pay_amt)
            assert ok, f"Payment recording failed: {pmsg}"
            print(f"   ✓ Payment (Rs.{pay_amt:.2f}) Recorded for Khatoo Record #{k_id}: {pmsg}")

            updated_khatoo = load_khatoo(test_cnic)
            new_due = float([k for k in updated_khatoo if k[0] == k_id][0][3])
            print(f"   ✓ New Outstanding Due Balance for #{k_id}: Rs.{new_due:.2f}")
        else:
            print("   ✓ All Khatoo records are fully settled (Rs.0.00 due).")

        print("\n" + "=" * 60)
        print(" 🎉 ALL 6 INTEGRATION CHECKS PASSED PERFECTLY!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_flow()
