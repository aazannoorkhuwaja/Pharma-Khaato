#!/usr/bin/env python3
"""Backend security and input-bounds verification.

Covers PBKDF2 storage, persistent brute-force lockout, CNIC normalization, LIKE
escaping, bounds on prices / batch quantities / discounts / repayments,
exclusive SQLite access, application-data placement and backup-restore safety.

Two things changed from the previous version of this suite:

* It now runs against a temporary data folder created for this process. It used
  to run against the owner's live application-data directory and to perform a
  real backup *and restore* there, which is not something a verification script
  should ever do to a shop computer.
* Its expectations follow the current operator contract. The repayment path now
  requires an authenticated staff member with an explicit payment reference, so
  a negative or oversized amount is rejected by
  ``core.credit_payment_service`` rather than by the retired two-argument shim.
  A rejection message tells the operator why; that wording is asserted here.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Isolate before importing anything that can resolve application data.
_DATA_DIR = tempfile.mkdtemp(prefix="pk-security-")
os.environ["PHARMA_KHAATO_DATA_DIR"] = _DATA_DIR
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.path_manager import PathManager  # noqa: E402

PathManager._BASE_DATA_DIR = None

from core.auth_service import hash_password_pbkdf2, login_user, verify_password  # noqa: E402
from core.credit_payment_service import record_customer_payment  # noqa: E402
from core.customer_service import escape_sql_like, validate_cnic  # noqa: E402
from core.inventory_service import add_batch, register_product  # noqa: E402
from core.pos_service import confirm_sale  # noqa: E402

ADMIN_USER = "security_admin"
ADMIN_PASSWORD = "SecretPassword123!"
CREDIT_CUSTOMER = "3520212345671"
CREDIT_BILL = 20.0


class TestBackendSecurity(unittest.TestCase):
    emp_id = 0

    @classmethod
    def setUpClass(cls):
        from core import auth_service
        from core.cash_session_service import open_session
        from core.db_engine import get_conn

        auth_service.register_initial_admin(ADMIN_USER, ADMIN_PASSWORD, "Security", "Admin")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT Employee_id FROM Employee WHERE username = %s", (ADMIN_USER,))
        cls.emp_id = int(cur.fetchone()[0])

        cur.execute(
            "INSERT INTO Supplier (supplier_name, supplier_company_name, Email_address, phone_number) "
            "VALUES ('Security Supplier', 'Security Co', 's@s.com', '0300')"
        )
        cur.execute(
            "INSERT INTO Products (product_name, company_name, category, barcode, stock_quantity, price) "
            "VALUES ('Security Med', 'Security Co', 'General', 'SEC1', 100, 20.0)"
        )
        cur.execute(
            "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
            "VALUES (1, 'SEC-LOT', 100, '2099-12-31', '2026-01-01', 1)"
        )
        cur.execute(
            "INSERT INTO Customers (id_card_number, first_name, last_name, Email_Address, city, registration_date) "
            "VALUES (%s, 'Credit', 'Customer', 'N/A', 'Karachi', '2026-01-01')",
            (CREDIT_CUSTOMER,),
        )
        cur.execute(
            "INSERT INTO Purchase (number_of_products, total_price, price_with_tax, customer_id, employee_id, "
            "payment_method, discount_amount) VALUES (1, ?, ?, ?, ?, 'Khatoo Credit', 0.0)",
            (CREDIT_BILL, CREDIT_BILL, CREDIT_CUSTOMER, cls.emp_id),
        )
        cur.execute(
            "INSERT INTO Customer_Khatoo (amount_paid, amount_due, purchase_id, customer_id, payment_method) "
            "VALUES (0.0, ?, 1, ?, 'Credit')",
            (CREDIT_BILL, CREDIT_CUSTOMER),
        )
        conn.commit()
        ok, detail = open_session(cls.emp_id, 0)
        assert ok, detail

    @classmethod
    def tearDownClass(cls):
        from core.db_engine import reset_thread_connections

        reset_thread_connections()
        os.environ.pop("PHARMA_KHAATO_DATA_DIR", None)
        PathManager._BASE_DATA_DIR = None
        shutil.rmtree(_DATA_DIR, ignore_errors=True)

    def test_pbkdf2_hashing_and_verification(self):
        password = "SecretPassword123!"
        hashed = hash_password_pbkdf2(password)
        self.assertTrue(hashed.startswith("pbkdf2:sha256:600000$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_cnic_validation(self):
        self.assertEqual(validate_cnic("35202-1234567-1"), "3520212345671")
        self.assertEqual(validate_cnic("3520212345671"), "3520212345671")
        self.assertIsNone(validate_cnic("123"))  # Too short
        self.assertIsNone(validate_cnic("352021234567A"))  # Non-numeric
        self.assertIsNone(validate_cnic("<script>alert(1)</script>"))  # Malicious input

    def test_sql_like_escaping(self):
        malicious_input = "Admin' OR '1'='1%_test"
        escaped = escape_sql_like(malicious_input)
        self.assertIn("\\%", escaped)
        self.assertIn("\\_", escaped)
        self.assertNotIn("%_test", escaped)

    def test_negative_and_zero_repayment_are_rejected(self):
        for amount, token in ((-50.0, "negative-repayment"), (0, "zero-repayment")):
            ok, msg, _meta = record_customer_payment(
                CREDIT_CUSTOMER, amount, self.emp_id, operation_id=token
            )
            self.assertFalse(ok, f"{amount} was accepted as a repayment")
            self.assertIn("greater than zero", msg.lower())

    def test_repayment_cannot_exceed_the_outstanding_balance(self):
        ok, msg, _meta = record_customer_payment(
            CREDIT_CUSTOMER, CREDIT_BILL * 25, self.emp_id, operation_id="overpayment"
        )
        self.assertFalse(ok, "an oversized repayment was accepted")
        self.assertIn("exceeds the remaining balance", msg.lower())

    def test_pos_negative_discount_rejection(self):
        cart = [{"prod_id": 1, "name": "Security Med", "price": 20.0, "batch_id": 1, "qty": 1, "subtotal": 20.0}]
        ok, msg = confirm_sale("WALKIN", self.emp_id, cart, total=20.0, discount=-10.0)
        self.assertFalse(ok, "a negative discount was accepted")
        self.assertIn("discount", msg.lower())

    def test_product_and_batch_bounds(self):
        ok, msg = register_product("Invalid Negative Price Item", -10.0)
        self.assertFalse(ok, "a negative selling price was accepted")
        self.assertIn("price", msg.lower())

        ok, msg = add_batch(1, 1, -5, "2028-12-31")
        self.assertFalse(ok, "a negative batch quantity was accepted")
        self.assertIn("range", msg.lower())

    def test_brute_force_lockout(self):
        target = f"brute_target_{uuid.uuid4().hex[:10]}"
        for _ in range(5):
            self.assertIsNone(login_user(target, "WrongPass"))
        with self.assertRaises(PermissionError):
            login_user(target, "WrongPass")

    def test_backup_and_restore_inside_the_disposable_shop(self):
        from core.backup_service import backup_database, restore_database
        from core.db_engine import get_conn

        get_conn()  # Ensure the isolated database file exists on disk.
        ok, path = backup_database()
        self.assertTrue(ok, path)
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.startswith(_DATA_DIR), "the backup left the disposable data folder")

        restored, message = restore_database(path)
        self.assertTrue(restored, message)

    def test_sqlite_exclusive_engine(self):
        from core.db_engine import get_conn

        conn = get_conn()
        self.assertEqual(conn.engine_type, "SQLite")
        self.assertTrue(conn.is_sqlite)

    def test_application_data_lives_in_the_chosen_folder(self):
        from core.path_manager import PathManager as PM

        for directory in (
            PM.get_base_data_dir(),
            PM.get_logs_dir(),
            PM.get_backups_dir(),
            PM.get_receipts_dir(),
        ):
            self.assertTrue(os.path.exists(directory), directory)
            self.assertTrue(os.path.abspath(directory).startswith(_DATA_DIR))


if __name__ == "__main__":
    print("=" * 60)
    print("  PHARMA-KHAATO BACKEND SECURITY VERIFICATION SUITE  ")
    print("=" * 60)
    print(f"  disposable shop: {_DATA_DIR}\n")
    unittest.main(verbosity=2)
