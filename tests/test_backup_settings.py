"""Backup/restore integrity and settings service."""


class TestBackup:
    def test_backup_and_restore_roundtrip(self, seeded_shop, cash_shift):
        from core import backup_service, pos_service, db_engine
        ok, msg = pos_service.confirm_sale(
            None, 1,
            [{"prod_id": 1, "name": "TestMed", "price": 15.0, "qty": 5}],
            payment_method="Cash",
        )
        assert ok
        okb, path = backup_service.backup_database()
        assert okb

        # Corrupt the live DB (drop a table)
        import sqlite3
        db = db_engine.PathManager.get_db_path()
        c = sqlite3.connect(db)
        c.execute("DROP TABLE Receipt")
        c.commit()
        c.close()

        okr, msgr = backup_service.restore_database(path)
        assert okr
        db_engine.reset_thread_connections()
        cur = db_engine.get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM Receipt")
        assert cur.fetchone()[0] == 1


class TestSettings:
    def test_small_percentage_keeps_percentage_units(self, seeded_shop, admin_emp_id):
        from core.settings_service import SettingsService
        from decimal import Decimal
        assert SettingsService.set_setting("default_tax_rate", "0.10", actor_id=admin_emp_id)
        assert SettingsService.get_tax_rate() == Decimal("0.001")

    def test_tax_rate_percentage_normalized(self, seeded_shop, admin_emp_id):
        from core.settings_service import SettingsService
        from decimal import Decimal
        assert SettingsService.set_setting("default_tax_rate", "18.0", actor_id=admin_emp_id)
        assert float(SettingsService.get_tax_rate()) == 0.18


def test_same_volume_copy_warns_without_preventing_snapshot(seeded_shop, tmp_path, monkeypatch):
    from pathlib import Path
    from core import backup_service as backup
    from core.health_service import SystemHealthService
    monkeypatch.delenv('PHARMA_KHAATO_BACKUP_DIR', raising=False)
    target = tmp_path / 'second-folder'
    ok, message = backup.configure_backup_destination(target)
    assert ok and 'same volume' in message
    assert backup.backup_destination_status()[0] == 'same_volume'
    health = SystemHealthService.run_diagnostics()
    assert health['backup_destination_status'] == 'same_volume'
    assert any('disk failure' in issue for issue in health['issues'])
    ok, snapshot = backup.backup_database()
    assert ok
    assert backup._validate_sqlite_database(target / Path(snapshot).name)[0]


def test_missing_and_disconnected_second_copy_need_attention(seeded_shop, tmp_path, monkeypatch):
    from core import backup_service as backup
    monkeypatch.delenv('PHARMA_KHAATO_BACKUP_DIR', raising=False)
    backup.configure_backup_destination('')
    assert backup.backup_destination_status()[0] == 'unconfigured'
    target = tmp_path / 'device'
    backup.configure_backup_destination(target)
    target.rmdir()
    assert backup.backup_destination_status()[0] == 'unavailable'
    assert not backup.backup_database()[0]


def test_environment_destination_is_checked_too(seeded_shop, tmp_path, monkeypatch):
    from core import backup_service as backup
    monkeypatch.setenv('PHARMA_KHAATO_BACKUP_DIR', str(tmp_path))
    assert backup.backup_destination_status()[0] == 'same_volume'
    monkeypatch.setenv('PHARMA_KHAATO_BACKUP_DIR', str(tmp_path / 'unmounted'))
    assert backup.backup_destination_status()[0] == 'unavailable'


def test_different_volume_does_not_claim_separate_physical_disk(seeded_shop, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from core import backup_service as backup
    target = tmp_path / 'other-volume'
    target.mkdir()
    monkeypatch.setenv('PHARMA_KHAATO_BACKUP_DIR', str(target))
    original_stat = backup.os.stat
    def stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if str(path) == str(target):
            return SimpleNamespace(st_dev=result.st_dev + 1, st_mode=result.st_mode)
        return result
    monkeypatch.setattr(backup.os, 'stat', stat)
    status, message = backup.backup_destination_status()
    assert status == 'different_volume'
    assert 'Confirm' in message and 'test restoring' in message


def test_replaced_backup_volume_is_not_reported_as_ready(seeded_shop, tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from core import backup_service as backup
    monkeypatch.delenv('PHARMA_KHAATO_BACKUP_DIR', raising=False)
    backup.configure_backup_destination(tmp_path / 'copy')
    config = Path(backup.PathManager.get_config_dir()) / 'backup.json'
    data = json.loads(config.read_text())
    data['device'] += 1
    config.write_text(json.dumps(data))
    assert backup.backup_destination_status()[0] == 'unavailable'
    assert not backup.backup_database()[0]
