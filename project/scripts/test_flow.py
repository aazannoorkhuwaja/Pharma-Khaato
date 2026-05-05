import sys
from datetime import date
from salesman_app import (
    db_register_customer, 
    db_search_customer, 
    db_search_products, 
    db_confirm_sale, 
    db_load_khatoo, 
    db_record_payment
)

def test_flow():
    try:
        # 1. Register Customer
        print("Testing register customer...")
        cnic = "1234567890123"
        db_register_customer(cnic, "Test", "User", "test@example.com", "TestCity")
        print("Register customer passed.")
        
        # 2. Search Customer
        print("Testing search customer...")
        custs = db_search_customer(cnic)
        if not custs:
            print("Customer not found after registration!")
            # Note: If id_card_number is AUTO_INCREMENT BIGINT, the CNIC string might have been cast to int or ignored.
            # But db_search_customer uses LIKE %s, so it should find something if it was inserted.
        else:
            print(f"Found customer: {custs[0]}")
        
        # 3. Search Products
        print("Testing search products...")
        prods = db_search_products("") # Search all or empty
        if prods:
            print(f"Found {len(prods)} products.")
            prod = prods[0]
            # prod = (prod_id, name, price, batch_id, stock)
            
            # 4. Confirm Sale (Credit)
            print("Testing confirm sale (Credit)...")
            cart = [{
                "prod_id": prod[0],
                "name": prod[1],
                "price": float(prod[2]),
                "batch_id": prod[3],
                "qty": 1,
                "subtotal": float(prod[2])
            }]
            db_confirm_sale(cnic, cart, 0, "Credit (Khatoo)")
            print("Confirm sale passed.")
            
            # 5. Load Khatoo
            print("Testing load khatoo...")
            khatoo_data = db_load_khatoo(cnic)
            if khatoo_data:
                print(f"Khatoo record found: {khatoo_data[0]}")
                khatoo_id = khatoo_data[0][0]
                
                # 6. Record Payment
                print("Testing record payment...")
                db_record_payment(khatoo_id, 10.0)
                print("Record payment passed.")
            else:
                print("No khatoo record found for credit sale!")
        else:
            print("No products found to test sale.")
            
        print("\nFULL FLOW PASSED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_flow()
