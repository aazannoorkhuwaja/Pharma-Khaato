import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.auth_service import login_user, hash_password_pbkdf2, verify_password
from core.customer_service import validate_cnic, escape_sql_like, register_customer, record_payment
from core.pos_service import confirm_sale

class TestBackendSecurity(unittest.TestCase):

    def test_pbkdf2_hashing_and_verification(self):
        password = "SecretPassword123!"
        hashed = hash_password_pbkdf2(password)
        self.assertTrue(hashed.startswith("pbkdf2:sha256:600000$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_cnic_validation(self):
        self.assertEqual(validate_cnic("35202-1234567-1"), "3520212345671")
        self.assertEqual(validate_cnic("3520212345671"), "3520212345671")
        self.assertIsNone(validate_cnic("123")) # Too short
        self.assertIsNone(validate_cnic("352021234567A")) # Non-numeric
        self.assertIsNone(validate_cnic("<script>alert(1)</script>")) # Malicious input

    def test_sql_like_escaping(self):
        malicious_input = "Admin' OR '1'='1%_test"
        escaped = escape_sql_like(malicious_input)
        self.assertIn("\\%", escaped)
        self.assertIn("\\_", escaped)
        self.assertNotIn("%_test", escaped)

    def test_khatoo_overpayment_and_negative_bound(self):
        # Negative payment rejection
        ok, msg = record_payment(1, -50.0)
        self.assertFalse(ok)
        self.assertIn("greater than zero", msg.lower())

        # Zero payment rejection
        ok, msg = record_payment(1, 0)
        self.assertFalse(ok)

    def test_pos_negative_discount_rejection(self):
        cart = [{"prod_id": 1, "name": "Panadol", "price": 20.0, "batch_id": 1, "qty": 1, "subtotal": 20.0}]
        ok, msg = confirm_sale("9990011223344", 1, cart, total=20.0, discount=-10.0)
        self.assertFalse(ok)
        self.assertIn("negative", msg.lower())

    def test_brute_force_lockout(self):
        fake_user = "brute_target_user"
        # 5 failed attempts
        for _ in range(5):
            res = login_user(fake_user, "WrongPass")
            self.assertIsNone(res)

        # 6th attempt should raise PermissionError lockout
        with self.assertRaises(PermissionError):
            login_user(fake_user, "WrongPass")

    def test_product_and_batch_bounds(self):
        from core.inventory_service import register_product, add_batch
        # Negative price rejection
        ok, msg = register_product("Test Invalid Item", -10.0)
        self.assertFalse(ok)
        self.assertIn("greater than zero", msg.lower())

        # Negative batch quantity rejection
        ok, msg = add_batch(1, 1, -5, "2028-12-31")
        self.assertFalse(ok)
    def test_backup_and_restore(self):
        from core.db_engine import get_conn
        from core.backup_service import backup_database, restore_database
        get_conn() # Ensure DB file is created on disk
        ok, path = backup_database()
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))
        
        rok, rmsg = restore_database(path)
        self.assertTrue(rok)

    def test_sqlite_exclusive_engine(self):
        from core.db_engine import get_conn
        conn = get_conn()
        self.assertEqual(conn.engine_type, "SQLite")
        self.assertTrue(conn.is_sqlite)

    def test_path_manager_directories(self):
        from core.path_manager import PathManager
        base_dir = PathManager.get_base_data_dir()
        self.assertTrue(os.path.exists(base_dir))
        self.assertTrue(os.path.exists(PathManager.get_logs_dir()))
        self.assertTrue(os.path.exists(PathManager.get_backups_dir()))
        self.assertTrue(os.path.exists(PathManager.get_receipts_dir()))

if __name__ == "__main__":
    print("============================================================")
    print("  PHARMA-KHAATO BACKEND SECURITY VERIFICATION SUITE  ")
    print("============================================================\n")
    unittest.main()
