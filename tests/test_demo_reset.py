"""Regression coverage for Windows-safe isolated demo resets."""

import os
from pathlib import Path

from scripts import demo_mode


def test_reset_keeps_open_logs_and_removes_demo_state(tmp_path, monkeypatch):
    demo_dir = tmp_path / ".demo-data"
    logs = demo_dir / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "app.log"
    log_file.write_text("diagnostic evidence", encoding="utf-8")
    data = demo_dir / "data"
    data.mkdir()
    (data / "pharmacy_db.sqlite").write_bytes(b"old demo database")
    (demo_dir / "stale.tmp").write_text("old", encoding="utf-8")

    monkeypatch.setattr(demo_mode, "ROOT", tmp_path)
    monkeypatch.setattr(demo_mode, "DEMO_DIR", demo_dir)
    monkeypatch.setenv("PHARMA_KHAATO_DATA_DIR", str(demo_dir))

    # Keep the handle open across reset; Windows would reject deleting it.
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("\\nopen handle")
        handle.flush()
        demo_mode.reset_demo_storage()
        assert log_file.exists()
        assert not data.exists()
        assert not (demo_dir / "stale.tmp").exists()
        handle.write("\\nstill writable")

    assert "diagnostic evidence" in log_file.read_text(encoding="utf-8")
