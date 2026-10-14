import json
import zipfile
from pathlib import Path


def test_support_bundle_excludes_business_data_and_contains_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("PHARMA_KHAATO_DATA_DIR", str(tmp_path / "product-data"))

    from core.path_manager import PathManager
    from core.db_engine import reset_thread_connections

    reset_thread_connections()
    PathManager._BASE_DATA_DIR = None

    # Create files that must never be swept into a support package.
    Path(PathManager.get_receipts_dir(), "receipt-123.txt").write_text("customer receipt", encoding="utf-8")
    Path(PathManager.get_exports_dir(), "business.csv").write_text("customer,balance", encoding="utf-8")
    Path(PathManager.get_backups_dir(), "manual.sqlite").write_bytes(b"not-real-business-data")

    from core.support_service import create_support_bundle

    ok, bundle_path = create_support_bundle()
    assert ok, bundle_path

    bundle = Path(bundle_path)
    assert bundle.exists()
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        assert "README.txt" in names
        assert "system.json" in names
        assert "readiness.json" in names
        assert not any(name.endswith(".sqlite") for name in names)
        assert not any("receipt-123" in name for name in names)
        assert not any("business.csv" in name for name in names)

        system = json.loads(archive.read("system.json"))
        assert system["product"] == "Pharma Khaato"
        assert system["version"]
        assert system["database_filename"] == "pharmacy_db.sqlite"

        readiness = json.loads(archive.read("readiness.json"))
        assert "checks" in readiness

    reset_thread_connections()
    PathManager._BASE_DATA_DIR = None
