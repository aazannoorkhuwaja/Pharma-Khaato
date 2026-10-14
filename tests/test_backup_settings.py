"""Backup/restore integrity and settings service."""


class TestBackup:
    def test_backup_and_restore_roundtrip(self, seeded_shop):
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
    def test_tax_rate_fraction_passthrough(self, fresh_db):
        from core.settings_service import SettingsService
        from decimal import Decimal
        SettingsService.set_setting("default_tax_rate", "0.10")
        assert float(SettingsService.get_tax_rate()) == 0.10

    def test_tax_rate_percentage_normalized(self, fresh_db):
        from core.settings_service import SettingsService
        from decimal import Decimal
        SettingsService.set_setting("default_tax_rate", "18.0")
        assert float(SettingsService.get_tax_rate()) == 0.18
