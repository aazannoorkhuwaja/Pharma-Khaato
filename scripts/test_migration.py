import unittest
import os
import sys
import sqlite3
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.migration_manager import MigrationManager
from core.backup_service import backup_database, restore_database
from core.inventory_service import add_batch
from core.pos_service import confirm_sale
from core.customer_service import record_payment

class TestMigrationEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_legacy.sqlite")
        
        # Create legacy database schema without new columns/tables
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE Employee (
                Employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                First_name TEXT NOT NULL,
                Last_name TEXT NOT NULL,
                occupation TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE Products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                stock_quantity INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE TABLE Customers (
                id_card_number TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL
            );
        """)
        conn.execute("""
            INSERT INTO Employee (Employee_id, username, password, First_name, Last_name, occupation)
            VALUES (1, 'legacy_admin', 'pass123', 'Legacy', 'Admin', 'Admin');
        """)
        conn.execute("""
            INSERT INTO Products (id, product_name, price, stock_quantity)
            VALUES (1, 'Legacy Aspirin', 10.0, 100);
        """)
        conn.execute("""
            INSERT INTO Customers (id_card_number, first_name, last_name)
            VALUES ('1111122222333', 'Legacy', 'Customer');
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legacy_schema_migration(self):
        conn = sqlite3.connect(self.db_path)
        # Apply authoritative migrations
        MigrationManager.apply_migrations(conn, is_sqlite=True)

        cur = conn.cursor()
        # Verify schema_migrations table tracked versions
        cur.execute("SELECT COUNT(*) FROM schema_migrations")
        self.assertGreater(cur.fetchone()[0], 0)

        # Verify old data survived
        cur.execute("SELECT product_name FROM Products WHERE id = 1")
        self.assertEqual(cur.fetchone()[0], "Legacy Aspirin")

        cur.execute("SELECT username FROM Employee WHERE Employee_id = 1")
        self.assertEqual(cur.fetchone()[0], "legacy_admin")

        conn.close()

if __name__ == "__main__":
    unittest.main()
