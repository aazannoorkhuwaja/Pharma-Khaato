"""Support diagnostics bundle creation.

A support bundle intentionally excludes the live database, receipts, exports and
backups. It contains only runtime metadata, readiness results and rotating app
logs so a deployment/support technician can diagnose a workstation without
receiving pharmacy business records by default.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from config import ApplicationSettings
from core.path_manager import PathManager
from core.readiness_service import run_readiness_checks


def _safe_json(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def create_support_bundle() -> tuple[bool, str]:
    """Create a privacy-conscious diagnostics ZIP in the exports directory."""
    try:
        exports = Path(PathManager.get_exports_dir())
        exports.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = exports / f"Pharma-Khaato-Support-{stamp}.zip"

        from core.lan_config import load_counter_config, enabled_counter_client
        if load_counter_config():
            try:
                readiness = {"mode": "counter", "shop_status": enabled_counter_client().public_status()}
            except Exception:
                readiness = {"mode": "counter", "ok": False, "message": "Main shop computer unavailable"}
        else:
            readiness = run_readiness_checks()
        manifest = {
            "product": ApplicationSettings.DISPLAY_NAME,
            "version": ApplicationSettings.APP_VERSION,
            "application_id": ApplicationSettings.APP_ID,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version,
            "frozen_build": bool(getattr(sys, "frozen", False)),
            "data_directory": PathManager.get_base_data_dir(),
            "database_filename": os.path.basename(PathManager.get_db_path()),
        }

        notice = (
            "Pharma Khaato Support Bundle\n"
            "===========================\n\n"
            "This bundle does NOT include the pharmacy database, receipts, exports, "
            "or backups. It contains runtime metadata, readiness results and application "
            "logs only. Logs can contain usernames, file paths and diagnostic messages; "
            "review the bundle before sharing it outside your organization.\n"
        )

        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("README.txt", notice)
            archive.writestr(
                "system.json",
                json.dumps({k: _safe_json(v) for k, v in manifest.items()}, indent=2, ensure_ascii=False),
            )
            archive.writestr(
                "readiness.json",
                json.dumps(readiness, indent=2, ensure_ascii=False, default=str),
            )

            logs_dir = Path(PathManager.get_logs_dir())
            for log_file in sorted(logs_dir.glob("app.log*")):
                if log_file.is_file():
                    archive.write(log_file, Path("logs") / log_file.name)

        if not out.exists() or out.stat().st_size <= 0:
            return False, "Support bundle could not be created."
        return True, str(out)
    except Exception as exc:
        return False, str(exc)
