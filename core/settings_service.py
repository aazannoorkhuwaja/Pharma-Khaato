from core.db_engine import get_db
from core.logger import get_logger
from config import PharmacySettings

logger = get_logger("PharmaKhaatoSettings")


class SettingsService:
    """Persistent administrative and regulatory settings."""

    @classmethod
    def _fallback_map(cls) -> dict[str, str]:
        return {
            "pharmacy_name": PharmacySettings.NAME,
            "slogan": PharmacySettings.SLOGAN,
            "address": PharmacySettings.ADDRESS,
            "phone": PharmacySettings.PHONE,
            "email": PharmacySettings.EMAIL,
            "license_number": PharmacySettings.LICENSE_NUMBER,
            "ntn_number": PharmacySettings.NTN_NUMBER,
            "receipt_footer": PharmacySettings.RECEIPT_FOOTER,
            "default_tax_rate": str(PharmacySettings.TAX_RATE),
            "near_expiry_days": str(PharmacySettings.NEAR_EXPIRY_DAYS),
        }

    @classmethod
    def get_many(cls, keys, defaults: dict | None = None) -> dict[str, str]:
        """Read many settings with one SQL round-trip.

        Missing keys fall back to explicit ``defaults`` first, then configured
        pharmacy defaults.  This keeps receipt rendering and Settings startup
        from issuing a separate query for every field.
        """
        clean_keys = tuple(dict.fromkeys(str(key) for key in keys if str(key)))
        defaults = defaults or {}
        fallback = cls._fallback_map()
        result = {
            key: str(defaults.get(key, fallback.get(key, "")) or "")
            for key in clean_keys
        }
        if not clean_keys:
            return result

        placeholders = ", ".join(["%s"] * len(clean_keys))
        try:
            with get_db() as (_conn, cur):
                cur.execute(
                    f"SELECT setting_key, setting_value FROM Pharmacy_Settings "
                    f"WHERE setting_key IN ({placeholders})",
                    clean_keys,
                )
                for key, value in cur.fetchall():
                    if value is not None:
                        result[str(key)] = str(value)
        except Exception as exc:
            logger.warning("Error reading settings batch: %s", exc)
        return result

    @classmethod
    def get_setting(cls, key: str, default_val: str = None) -> str:
        values = cls.get_many([key], {key: default_val or ""})
        return values.get(key, default_val or "")

    @classmethod
    def set_setting(cls, key: str, value: str) -> bool:
        return cls.update_settings({key: value})

    @classmethod
    def get_all_settings(cls) -> dict:
        keys = [
            "pharmacy_name", "slogan", "address", "phone", "email",
            "license_number", "ntn_number", "receipt_footer",
            "default_tax_rate", "near_expiry_days",
        ]
        return cls.get_many(keys)

    @classmethod
    def get_tax_rate(cls) -> "Decimal":
        """Return the configured tax rate as a scaled Decimal fraction."""
        from decimal import Decimal, ROUND_HALF_UP

        try:
            raw = cls.get_setting("default_tax_rate", str(PharmacySettings.TAX_RATE))
            val = float(raw)
            if val > 1.0:
                val = val / 100.0
            return Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal(str(PharmacySettings.TAX_RATE))

    @classmethod
    def update_settings(cls, settings_dict: dict) -> bool:
        """Save multiple settings atomically in one transaction."""
        if not settings_dict:
            return True
        try:
            with get_db() as (_conn, cur):
                for key, value in settings_dict.items():
                    key = str(key)
                    value = str(value)
                    cur.execute(
                        "SELECT setting_key FROM Pharmacy_Settings WHERE setting_key = %s",
                        (key,),
                    )
                    if cur.fetchone():
                        cur.execute(
                            "UPDATE Pharmacy_Settings SET setting_value = %s WHERE setting_key = %s",
                            (value, key),
                        )
                    else:
                        cur.execute(
                            "INSERT INTO Pharmacy_Settings (setting_key, setting_value) VALUES (%s, %s)",
                            (key, value),
                        )
            return True
        except Exception as exc:
            logger.error("Error saving settings batch: %s", exc)
            return False
