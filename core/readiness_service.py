"""Launch-readiness checks for installed and development builds.

The checks are intentionally read-mostly and safe to run before a demo or
release.  They verify that the local runtime can create its working folders,
open the SQLite database, apply the current schema/migrations, and persist
files without requiring a configured pharmacy or staff account yet.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict

from core.db_engine import get_conn
from core.path_manager import PathManager


REQUIRED_TABLES = {
    "Employee",
    "Customers",
    "Supplier",
    "Products",
    "Batch",
    "Purchase",
    "Sales_details",
    "Receipt",
    "Customer_Khatoo",
    "Pharmacy_Settings",
    "Cash_Register_Session",
    "Cash_Movement",
    "Credit_Payment",
}


@dataclass
class ReadinessCheck:
    name: str
    ok: bool
    detail: str
    warning: bool = False


def _probe_writable_directory(path: str, label: str) -> ReadinessCheck:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".pharma-khaato-write-test")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(probe)
        return ReadinessCheck(label, True, path)
    except Exception as exc:
        return ReadinessCheck(label, False, f"{path}: {exc}")


def run_readiness_checks() -> dict:
    checks: list[ReadinessCheck] = []

    # The app must never depend on the executable directory being writable.
    folders = (
        (PathManager.get_base_data_dir(), "Application data folder"),
        (PathManager.get_logs_dir(), "Logs folder"),
        (PathManager.get_backups_dir(), "Backups folder"),
        (PathManager.get_receipts_dir(), "Receipts folder"),
        (PathManager.get_exports_dir(), "Exports folder"),
        (PathManager.get_config_dir(), "Config folder"),
    )
    for path, label in folders:
        checks.append(_probe_writable_directory(path, label))

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        checks.append(ReadinessCheck("Database connection", True, PathManager.get_db_path()))

        cur.execute("PRAGMA quick_check")
        row = cur.fetchone()
        integrity = str(row[0]).lower() if row else "unknown"
        checks.append(
            ReadinessCheck(
                "Database integrity",
                integrity == "ok",
                integrity,
            )
        )

        cur.execute("PRAGMA foreign_keys")
        fk_row = cur.fetchone()
        fk_on = bool(fk_row and int(fk_row[0]) == 1)
        checks.append(ReadinessCheck("Foreign-key enforcement", fk_on, "enabled" if fk_on else "disabled"))

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {str(row[0]) for row in cur.fetchall()}
        missing = sorted(REQUIRED_TABLES - existing)
        checks.append(
            ReadinessCheck(
                "Required database schema",
                not missing,
                "all required tables present" if not missing else "missing: " + ", ".join(missing),
            )
        )

        # Re-derive the money and stock facts a pharmacy has to be able to
        # trust. Drift here means real damage (a partial restore or a file that
        # changed outside the application), so it is a failure, not a warning.
        from core.integrity_service import reconcile

        reconciliation = reconcile()
        if reconciliation["ok"]:
            checks.append(
                ReadinessCheck(
                    "Business data reconciliation",
                    True,
                    f"{reconciliation['checks_run']} accounting identities match",
                )
            )
        else:
            drift = ", ".join(
                f"{item['check']} ({item['count']})" for item in reconciliation["findings"]
            )
            checks.append(
                ReadinessCheck(
                    "Business data reconciliation",
                    False,
                    "drift detected; restore a verified backup and contact support: " + drift,
                )
            )

        cur.execute("SELECT COUNT(*) FROM Employee")
        employee_count = int((cur.fetchone() or [0])[0] or 0)
        checks.append(
            ReadinessCheck(
                "Initial setup",
                True,
                f"{employee_count} staff account(s) configured" if employee_count else "first-run setup is still required",
                warning=(employee_count == 0),
            )
        )
    except Exception as exc:
        checks.append(ReadinessCheck("Database startup", False, str(exc)))

    try:
        usage = shutil.disk_usage(PathManager.get_base_data_dir())
        free_mb = usage.free / (1024 * 1024)
        low = free_mb < 200
        critical = free_mb < 50
        checks.append(
            ReadinessCheck(
                "Free disk space",
                not critical,
                f"{free_mb:.0f} MB free",
                warning=(low and not critical),
            )
        )
    except Exception as exc:
        checks.append(ReadinessCheck("Free disk space", True, f"unavailable: {exc}", warning=True))

    failed = [item for item in checks if not item.ok]
    warnings = [item for item in checks if item.warning]
    return {
        "ok": not failed,
        "checks": [asdict(item) for item in checks],
        "failed_count": len(failed),
        "warning_count": len(warnings),
        "data_dir": PathManager.get_base_data_dir(),
        "db_path": PathManager.get_db_path(),
    }


def format_readiness_report(report: dict) -> str:
    lines = ["Pharma-Khaato launch self-check"]
    for item in report.get("checks", []):
        if not item.get("ok"):
            marker = "FAIL"
        elif item.get("warning"):
            marker = "WARN"
        else:
            marker = "PASS"
        lines.append(f"[{marker}] {item.get('name')}: {item.get('detail')}")
    lines.append(
        "READY" if report.get("ok") else f"NOT READY ({report.get('failed_count', 0)} failed check(s))"
    )
    return "\n".join(lines)
