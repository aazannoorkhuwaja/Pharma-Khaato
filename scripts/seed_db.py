import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db_engine import get_conn
from core.customer_service import register_customer
from core.inventory_service import register_product, register_supplier, add_batch, clear_inventory_cache

def seed_database():
    print("Seeding Pharma-Khaato database with sample records...")
    
    # 0. Initial Employee
    from core.auth_service import register_initial_admin
    register_initial_admin("admin", "admin123", "Admin", "User")

    # 1. Customers
    customers = [
        ("3520212345671", "Ahmed", "Khan", "ahmed.k@email.com", "Peshawar"),
        ("3520212345672", "Sara", "Ali", "sara.a@email.com", "Islamabad"),
        ("3520212345673", "Usman", "Tariq", "usman.t@email.com", "Lahore"),
        ("3520212345674", "Zainab", "Fatima", "zainab.f@email.com", "Karachi"),
    ]
    for c in customers:
        ok, msg = register_customer(*c)
        print(f"Customer {c[1]} {c[2]}: {msg}")

    # 2. Suppliers
    suppliers = [
        ("MediDistro", "03001234567", "National Pharma Ltd", "contact@natpharma.pk"),
        ("BioMed Supplies", "03219876543", "BioMed Corp", "sales@biomed.pk"),
        ("CureAll Pharma", "03335557799", "CureAll Traders", "info@cureall.pk"),
    ]
    for s in suppliers:
        ok, msg = register_supplier(s[0], s[1], s[2], s[3])
        print(f"Supplier {s[0]}: {msg}")

    # 3. Master Products
    products = [
        ("Panadol 500mg", 50.00, 100, "GSK", "Analgesic", "Paracetamol 500mg"),
        ("Augmentin 625mg", 450.00, 20, "GSK", "Antibiotic", "Amoxicillin + Clavulanate"),
        ("Brufen 400mg", 80.00, 50, "Abbott", "NSAID", "Ibuprofen 400mg"),
        ("Disprin 300mg", 30.00, 30, "Reckitt", "Analgesic", "Aspirin 300mg"),
        ("Surbex Z", 220.00, 40, "Abbott", "Multivitamin", "Zinc + Vitamin B-Complex"),
        ("Flymax Syrup", 120.00, 25, "Getz", "Antihistamine", "Cetirizine 5mg/5ml"),
    ]
    for p in products:
        ok, msg = register_product(p[0], p[1], p[2], p[3], p[4], p[5])
        print(f"Product {p[0]}: {msg}")

    # 4. Add Batches using real product IDs
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, product_name FROM Products")
    prod_map = {row[1]: row[0] for row in cur.fetchall()}
    conn.close()

    batch_specs = [
        ("Panadol 500mg", 1, 1000, "2028-05-01", "2026-01-01"),
        ("Augmentin 625mg", 1, 200, "2027-12-15", "2025-12-01"),
        ("Brufen 400mg", 2, 500, "2027-08-20", "2026-02-10"),
        ("Disprin 300mg", 2, 300, "2026-09-01", "2025-09-01"),
        ("Surbex Z", 3, 150, "2028-01-15", "2026-01-15"),
        ("Flymax Syrup", 3, 80,  "2027-11-30", "2025-11-01"),
    ]

    for pname, supp_id, qty, exp_date, mfg_date in batch_specs:
        pid = prod_map.get(pname)
        if pid:
            ok, msg = add_batch(pid, supp_id, qty, exp_date, mfg_date)
            print(f"Batch for '{pname}' (ID #{pid}): {msg}")

    clear_inventory_cache()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
