import unittest
import os
import sys
import psutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db_engine import get_conn
from core.inventory_service import search_products
from core.reports_service import get_daily_sales_report
from core.backup_service import backup_database, restore_database

class TestResourceAndConnectionLeaks(unittest.TestCase):
    def test_repeated_connections_and_queries(self):
        process = psutil.Process(os.getpid())
        initial_fds = process.num_fds() if hasattr(process, 'num_fds') else 0

        # Execute 100 repeated queries & connection cycles
        for _ in range(100):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM Products")
            cur.fetchone()
            conn.close()

        final_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        if initial_fds > 0:
            fd_diff = abs(final_fds - initial_fds)
            self.assertLess(fd_diff, 10, f"Possible file descriptor leak detected: {fd_diff} accumulative open files.")

    def test_repeated_report_generation(self):
        for _ in range(20):
            rpt = get_daily_sales_report()
            self.assertIsNotNone(rpt)

    def test_backup_restore_no_lock(self):
        get_conn()
        ok, backup_path = backup_database()
        if ok and os.path.exists(backup_path):
            rok, msg = restore_database(backup_path)
            self.assertTrue(rok, f"Restore failed: {msg}")

if __name__ == "__main__":
    unittest.main()
