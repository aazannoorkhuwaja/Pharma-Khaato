"""Platform-neutral startup/runtime health diagnostics."""

import os
from typing import Any

from core.path_manager import PathManager
from core.db_engine import get_conn


class SystemHealthService:
    @staticmethod
    def run_diagnostics() -> dict[str, Any]:
        results = {
            "db_connected": False,
            "db_path": PathManager.get_db_path(),
            "receipts_dir": PathManager.get_receipts_dir(),
            "backups_dir": PathManager.get_backups_dir(),
            "logs_dir": PathManager.get_logs_dir(),
            "wal_enabled": False,
            "db_integrity_ok": False,
            "free_space_mb": 0,
            "writable_directories": False,
            "issues": [],
        }

        dirs_to_check = [results["receipts_dir"], results["backups_dir"], results["logs_dir"]]
        all_writable = True
        for directory in dirs_to_check:
            try:
                os.makedirs(directory, exist_ok=True)
                if not os.access(directory, os.W_OK):
                    all_writable = False
                    results["issues"].append(f"Directory non-writable: {directory}")
            except OSError as exc:
                all_writable = False
                results["issues"].append(f"Directory error ({directory}): {exc}")
        results["writable_directories"] = all_writable

        try:
            conn = get_conn()
            results["db_connected"] = True
            if conn.is_sqlite:
                cur = conn.cursor()
                cur.execute("PRAGMA journal_mode;")
                row = cur.fetchone()
                results["wal_enabled"] = bool(row and str(row[0]).lower() == "wal")
                if not results["wal_enabled"]:
                    results["issues"].append("SQLite WAL mode disabled")
                cur.execute("PRAGMA quick_check;")
                check = cur.fetchone()
                results["db_integrity_ok"] = bool(check and str(check[0]).lower() == "ok")
                if not results["db_integrity_ok"]:
                    results["issues"].append("Database integrity check failed")
            else:
                results["wal_enabled"] = True
                results["db_integrity_ok"] = True
            conn.close()
        except Exception as exc:
            results["issues"].append(f"Database error: {exc}")

        try:
            stat = os.statvfs(PathManager.get_base_data_dir())
            results["free_space_mb"] = int((stat.f_bavail * stat.f_frsize) / (1024 * 1024))
            if results["free_space_mb"] < 200:
                results["issues"].append("Less than 200 MB free space is available for data and backups")
        except (AttributeError, OSError):
            # Windows does not expose statvfs; disk-space reporting is optional there.
            pass

        return results
