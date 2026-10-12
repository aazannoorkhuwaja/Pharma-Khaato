from core.db_engine import get_db
from core.logger import get_logger
from config import PharmacySettings

logger = get_logger("PharmaKhaatoSettings")


class SettingsService:
    """
    Manages persistent administrative and regulatory settings in the database.
    Persistent application settings backed by the local SQLite database.
    """

    @classmethod
    def get_setting(cls, key: str, default_val: str = None) -> str:
        try:
            with get_db() as (conn, cur):
                cur.execute(
                    "SELECT setting_value FROM Pharmacy_Settings WHERE setting_key = %s", (key,)
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    return row[0]
        except Exception as e:
            logger.warning(f"Error reading setting '{key}' from DB: {e}")

        # Fallback to environment/config defaults
        fallback_map = {
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
        return fallback_map.get(key, default_val or "")

    @classmethod
    def set_setting(cls, key: str, value: str) -> bool:
        try:
            with get_db() as (conn, cur):
                cur.execute(
                    "SELECT setting_key FROM Pharmacy_Settings WHERE setting_key = %s", (key,)
                )
                if cur.fetchone():
                    cur.execute(
                        "UPDATE Pharmacy_Settings SET setting_value = %s WHERE setting_key = %s",
                        (str(value), key),
                    )
                else:
                    cur.execute(
                        "INSERT INTO Pharmacy_Settings (setting_key, setting_value) VALUES (%s, %s)",
                        (key, str(value)),
                    )
            return True
        except Exception as e:
            logger.error(f"Error saving setting '{key}' = '{value}': {e}")
            return False

    @classmethod
    def get_all_settings(cls) -> dict:
        keys = [
            "pharmacy_name", "slogan", "address", "phone", "email",
            "license_number", "ntn_number", "receipt_footer",
            "default_tax_rate", "near_expiry_days",
        ]
        return {k: cls.get_setting(k) for k in keys}

    @classmethod
    def get_tax_rate(cls) -> "Decimal":
        """
        Returns the configured tax rate as a properly scaled Decimal fraction.

        Normalisation rules (one place, tested once, applied everywhere):
          - DB / env value "10.0"  → Decimal("0.10")   (percentage format, >1.0)
          - DB / env value "0.10"  → Decimal("0.10")   (already a fraction)
          - DB / env value "0"     → Decimal("0.00")   (zero tax)
          - Any parse failure      → PharmacySettings.TAX_RATE as Decimal fallback

        Callers receive a ready-to-multiply Decimal with no further normalisation needed.
        """
        from decimal import Decimal, ROUND_HALF_UP
        try:
            raw = cls.get_setting("default_tax_rate", str(PharmacySettings.TAX_RATE))
            val = float(raw)
            if val > 1.0:          # percentage format, e.g. 10.0 → 0.10
                val = val / 100.0
            return Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        except Exception:
            from decimal import Decimal
            return Decimal(str(PharmacySettings.TAX_RATE))

    @classmethod
    def update_settings(cls, settings_dict: dict) -> bool:
        for k, v in settings_dict.items():
            if not cls.set_setting(k, v):
                return False
        return True
