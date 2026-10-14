#!/usr/bin/env python3
"""Prepare and launch a deterministic, isolated Pharma-Khaato demo.

The demo database lives under ``.demo-data`` in the repository and is never the
normal user data directory.  Running this script without flags resets the demo
to a known state, validates it, prints credentials/talking points, and launches
the real application against that isolated data.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = (ROOT / ".demo-data").resolve()

# Must be set before any core module resolves PathManager.
os.environ["PHARMA_KHAATO_DATA_DIR"] = str(DEMO_DIR)
os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", ""))
sys.path.insert(0, str(ROOT))

DEMO_ADMIN_USER = "admin"
DEMO_ADMIN_PASSWORD = "demo1234"
DEMO_CASHIER_USER = "cashier"
DEMO_CASHIER_PASSWORD = "demo1234"


def _assert_demo_path() -> None:
    configured = Path(os.environ["PHARMA_KHAATO_DATA_DIR"]).resolve()
    if configured != DEMO_DIR:
        raise RuntimeError(f"Refusing demo reset outside isolated path: {configured}")
    if configured == ROOT or ROOT not in configured.parents:
        raise RuntimeError(f"Unsafe demo directory rejected: {configured}")


def reset_demo_storage() -> None:
    _assert_demo_path()
    try:
        from core import db_engine
        db_engine.reset_thread_connections()
    except Exception:
        pass
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    from core.path_manager import PathManager
    PathManager._BASE_DATA_DIR = None


def _must(result, label: str):
    ok, detail = result
    if not ok:
        raise RuntimeError(f"{label} failed: {detail}")
    return detail


def _product_lookup(name: str):
    from core.inventory_service import search_products, clear_inventory_cache
    clear_inventory_cache()
    rows = search_products(name)
    for row in rows:
        if str(row[1]).strip().lower() == name.strip().lower():
            return row
    raise RuntimeError(f"Demo product not found after seeding: {name}")


def _sale(employee_id: int, product_name: str, qty: int, payment_method: str, customer_id: str = "WALKIN") -> int:
    from core.pos_service import confirm_sale

    product = _product_lookup(product_name)
    cart = [{
        "prod_id": product[0],
        "name": product[1],
        "price": float(product[2]),
        "batch_id": product[3],
        "qty": int(qty),
        "subtotal": float(product[2]) * int(qty),
    }]
    total = cart[0]["subtotal"]
    ok, message = confirm_sale(
        customer_id,
        employee_id,
        cart,
        total=total,
        discount=0.0,
        payment_method=payment_method,
    )
    if not ok:
        raise RuntimeError(f"Demo {payment_method} sale failed: {message}")
    try:
        return int(str(message).split("Sale #", 1)[1].split()[0])
    except Exception:
        from core.db_engine import get_db
        with get_db() as (_conn, cur):
            cur.execute("SELECT MAX(purchase_id) FROM Purchase")
            return int((cur.fetchone() or [0])[0] or 0)


def seed_demo_database() -> dict:
    """Create a complete demo using the same services used by the real app."""
    _assert_demo_path()

    from core.db_engine import get_conn, get_db
    from core.auth_service import register_initial_admin, create_employee
    from core.customer_service import register_customer
    from core.inventory_service import register_supplier, register_product, add_batch, clear_inventory_cache
    from core.settings_service import SettingsService
    from core.cash_session_service import open_session
    from core.credit_payment_service import record_credit_payment

    # Force schema creation/migrations before using business services.
    conn = get_conn()
    conn.cursor().execute("SELECT 1")

    _must(register_initial_admin(DEMO_ADMIN_USER, DEMO_ADMIN_PASSWORD, "Ahsan", "Malik"), "Admin setup")
    _must(create_employee(DEMO_CASHIER_USER, DEMO_CASHIER_PASSWORD, "Sara", "Khan", "Salesman"), "Cashier setup")

    if not SettingsService.update_settings({
        "pharmacy_name": "CityCare Pharmacy & Surgical",
        "slogan": "Trusted medicines, safer care",
        "address": "Main Boulevard, Lahore",
        "phone": "042-111-227-300",
        "email": "care@citycare.demo",
        "license_number": "DRAP-DEMO-2026-0147",
        "ntn_number": "1234567-8",
        "receipt_footer": "Medicines once sold are subject to pharmacy return policy.",
        "default_tax_rate": "0.00",
        "near_expiry_days": "30",
        "max_customer_credit_limit": "25000.00",
        "receipt_template": "professional_80",
    }):
        raise RuntimeError("Could not save demo pharmacy settings.")

    customers = [
        ("3520212345671", "Ahmed", "Raza", "ahmed.raza@demo.pk", "Lahore"),
        ("3520212345672", "Maryam", "Ali", "maryam.ali@demo.pk", "Lahore"),
        ("3520212345673", "Usman", "Tariq", "usman.tariq@demo.pk", "Kasur"),
        ("3520212345674", "Zainab", "Fatima", "zainab.fatima@demo.pk", "Lahore"),
    ]
    for customer in customers:
        _must(register_customer(*customer), f"Customer {customer[1]}")

    suppliers = [
        ("MediLink Distributors", "03001234567", "MediLink Pakistan", "orders@medilink.demo"),
        ("HealthBridge Supply", "03219876543", "HealthBridge Traders", "sales@healthbridge.demo"),
        ("Prime Surgical", "03335557799", "Prime Surgical Pvt Ltd", "supply@primesurgical.demo"),
    ]
    for supplier in suppliers:
        _must(register_supplier(*supplier), f"Supplier {supplier[0]}")

    products = [
        dict(name="Panadol 500mg", price=55, min_stock=40, company="GSK", category="Analgesic", formula="Paracetamol", barcode="8961001000001", sku="PAN500", generic_name="Paracetamol", dosage_form="Tablet", strength="500mg", pack_size=20, rack_location="A-01"),
        dict(name="Augmentin 625mg", price=485, min_stock=20, company="GSK", category="Antibiotic", formula="Amoxicillin + Clavulanate", barcode="8961001000002", sku="AUG625", generic_name="Co-amoxiclav", dosage_form="Tablet", strength="625mg", pack_size=6, rack_location="A-05", requires_prescription=1),
        dict(name="Brufen 400mg", price=85, min_stock=30, company="Abbott", category="NSAID", formula="Ibuprofen", barcode="8961001000003", sku="BRU400", generic_name="Ibuprofen", dosage_form="Tablet", strength="400mg", pack_size=20, rack_location="A-03"),
        dict(name="ORS Sachet", price=45, min_stock=25, company="Searle", category="Rehydration", formula="Oral Rehydration Salts", barcode="8961001000004", sku="ORS01", generic_name="ORS", dosage_form="Sachet", strength="WHO Formula", pack_size=1, rack_location="B-02"),
        dict(name="Cetirizine 10mg", price=35, min_stock=20, company="Getz", category="Antihistamine", formula="Cetirizine", barcode="8961001000005", sku="CET10", generic_name="Cetirizine", dosage_form="Tablet", strength="10mg", pack_size=10, rack_location="B-05"),
        dict(name="Vitamin C 500mg", price=120, min_stock=15, company="Nutrifactor", category="Supplement", formula="Ascorbic Acid", barcode="8961001000006", sku="VITC500", generic_name="Ascorbic Acid", dosage_form="Tablet", strength="500mg", pack_size=30, rack_location="C-01"),
        dict(name="Surgical Gloves Medium", price=75, min_stock=20, company="Prime", category="Surgical", formula="N/A", barcode="8961001000007", sku="GLV-M", generic_name="Examination Gloves", dosage_form="Unit", strength="Medium", pack_size=1, rack_location="S-02"),
    ]
    for product in products:
        _must(register_product(**product), f"Product {product['name']}")

    with get_db() as (_conn, cur):
        cur.execute("SELECT id, supplier_name FROM Supplier")
        supplier_ids = {row[1]: row[0] for row in cur.fetchall()}
        cur.execute("SELECT id, product_name FROM Products")
        product_ids = {row[1]: row[0] for row in cur.fetchall()}
        cur.execute("SELECT Employee_id, username FROM Employee")
        employee_ids = {row[1]: row[0] for row in cur.fetchall()}

    today = date.today()
    batch_plan = [
        ("Panadol 500mg", "MediLink Distributors", 180, today + timedelta(days=120)),
        ("Panadol 500mg", "HealthBridge Supply", 260, today + timedelta(days=365)),
        ("Augmentin 625mg", "MediLink Distributors", 55, today + timedelta(days=240)),
        ("Brufen 400mg", "HealthBridge Supply", 90, today + timedelta(days=190)),
        # Intentionally low stock: 8 units vs reorder level 25.
        ("ORS Sachet", "HealthBridge Supply", 8, today + timedelta(days=300)),
        ("Cetirizine 10mg", "MediLink Distributors", 60, today + timedelta(days=160)),
        # Intentionally near expiry for the alert/demo workflow.
        ("Vitamin C 500mg", "MediLink Distributors", 25, today + timedelta(days=14)),
        ("Surgical Gloves Medium", "Prime Surgical", 70, today + timedelta(days=720)),
    ]
    mfg = (today - timedelta(days=90)).isoformat()
    for product_name, supplier_name, qty, expiry in batch_plan:
        _must(
            add_batch(product_ids[product_name], supplier_ids[supplier_name], qty, expiry.isoformat(), mfg),
            f"Stock {product_name}",
        )

    clear_inventory_cache()
    admin_id = int(employee_ids[DEMO_ADMIN_USER])
    _must(open_session(admin_id, 5000.00), "Demo cash shift")

    # A mix of tenders makes Reports and Shift & Cash immediately meaningful.
    sale_ids = {
        "cash": _sale(admin_id, "Panadol 500mg", 2, "Cash"),
        "card": _sale(admin_id, "Augmentin 625mg", 1, "Credit Card", customers[0][0]),
        "easypaisa": _sale(admin_id, "Cetirizine 10mg", 2, "Easypaisa", customers[1][0]),
        "jazzcash": _sale(admin_id, "Surgical Gloves Medium", 2, "JazzCash", customers[2][0]),
        "credit": _sale(admin_id, "Brufen 400mg", 4, "Khatoo Credit", customers[3][0]),
    }

    with get_db() as (_conn, cur):
        cur.execute(
            "SELECT id, amount_due FROM Customer_Khatoo WHERE purchase_id = %s ORDER BY id DESC LIMIT 1",
            (sale_ids["credit"],),
        )
        ledger = cur.fetchone()
    if not ledger:
        raise RuntimeError("Demo credit ledger was not created.")
    partial = min(100.0, float(ledger[1]))
    _must(
        record_credit_payment(ledger[0], partial, admin_id, "Cash", "Demo partial credit collection"),
        "Demo credit repayment",
    )

    # Final integrity/readiness check is part of preparing the demo, not optional.
    from core.readiness_service import run_readiness_checks
    report = run_readiness_checks()
    if not report.get("ok"):
        failed = [item for item in report.get("checks", []) if not item.get("ok")]
        raise RuntimeError("Demo readiness failed: " + "; ".join(item.get("detail", "") for item in failed))

    return {
        "admin_id": admin_id,
        "cashier_id": int(employee_ids[DEMO_CASHIER_USER]),
        "sale_ids": sale_ids,
        "credit_ledger_id": int(ledger[0]),
        "data_dir": str(DEMO_DIR),
    }


def print_demo_card(summary: dict) -> None:
    sales = summary.get("sale_ids", {})
    print("\n" + "=" * 68)
    print("PHARMA-KHAATO DEMO READY")
    print("=" * 68)
    print(f"Isolated demo data: {summary.get('data_dir')}")
    print(f"Admin login:   {DEMO_ADMIN_USER} / {DEMO_ADMIN_PASSWORD}")
    print(f"Cashier login: {DEMO_CASHIER_USER} / {DEMO_CASHIER_PASSWORD}")
    print("\nDemo already contains:")
    print("  • Open admin cash shift with Rs. 5,000 starting cash")
    print("  • Cash, Card, Easypaisa, JazzCash and Customer Credit sales")
    print("  • Partial cash collection against Customer Credit")
    print("  • Low-stock and near-expiry products")
    print("  • Professional 80mm receipt configuration")
    print(f"  • Return-ready sale numbers: {', '.join(str(v) for v in sales.values())}")
    print("\nRecommended live demo: New Sale → Customers → Customer Credit →")
    print("Stock & Products → Shift & Cash → Reports → Returns → Settings/Receipts")
    print("=" * 68 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset and launch the isolated Pharma-Khaato demo")
    parser.add_argument("--keep", action="store_true", help="Reuse existing .demo-data instead of resetting it")
    parser.add_argument("--no-launch", action="store_true", help="Prepare/check demo data and exit without opening the UI")
    parser.add_argument("--self-check", action="store_true", help="Only run readiness checks against the demo database")
    args = parser.parse_args()

    _assert_demo_path()

    if args.self_check:
        from core.readiness_service import run_readiness_checks, format_readiness_report
        report = run_readiness_checks()
        print(format_readiness_report(report))
        return 0 if report.get("ok") else 2

    db_file = DEMO_DIR / "data" / "pharmacy_db.sqlite"
    if not args.keep or not db_file.exists():
        reset_demo_storage()
        summary = seed_demo_database()
    else:
        from core.readiness_service import run_readiness_checks
        report = run_readiness_checks()
        if not report.get("ok"):
            raise RuntimeError("Existing demo data failed readiness checks; rerun without --keep.")
        summary = {"data_dir": str(DEMO_DIR), "sale_ids": {}}

    print_demo_card(summary)
    if args.no_launch:
        return 0

    env = os.environ.copy()
    env["PHARMA_KHAATO_DATA_DIR"] = str(DEMO_DIR)
    return subprocess.call([sys.executable, str(ROOT / "main.py")], cwd=str(ROOT), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
