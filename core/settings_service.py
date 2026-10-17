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
            raise RuntimeError("Shop settings could not be read. Reconnect or retry before continuing.") from exc
        return result

    @classmethod
    def get_setting(cls, key: str, default_val: str = None) -> str:
        values = cls.get_many([key], {key: default_val or ""})
        return values.get(key, default_val or "")

    @classmethod
    def set_setting(cls, key: str, value: str, actor_id=None) -> bool:
        return cls.update_settings({key: value}, actor_id=actor_id)

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
        """Read the canonical percentage; ambiguous legacy values require review."""
        from decimal import Decimal, InvalidOperation
        with get_db() as (_conn, cur):
            cur.execute("SELECT setting_key,setting_value FROM Pharmacy_Settings WHERE setting_key IN ('default_tax_rate','default_tax_rate_format','tax_rate_review_required')")
            settings = dict(cur.fetchall())
        if not all(key in settings for key in ("default_tax_rate", "default_tax_rate_format", "tax_rate_review_required")):
            raise ValueError("Sales tax settings are incomplete. Review Settings before completing sales.")
        if settings["tax_rate_review_required"] == "1":
            raise ValueError("Review and save Sales tax in Settings before completing sales. An older tax value had ambiguous units.")
        try:
            percentage = Decimal(settings["default_tax_rate"])
            if settings["default_tax_rate_format"] != "percent_v1" or not percentage.is_finite() or not 0 <= percentage <= 50:
                raise ValueError()
            return percentage / Decimal("100")
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("Sales tax must be a percentage between 0 and 50. Review Settings.") from exc

    @classmethod
    def update_settings(cls, settings_dict: dict, actor_id=None) -> bool:
        """Save multiple settings atomically in one transaction."""
        if not settings_dict:
            return True
        try:
            from core.permission_service import require_permission
            allowed, reason = require_permission(actor_id, "settings.manage")
            if not allowed:
                logger.warning("Settings update denied: %s", reason)
                return False
            settings_dict = dict(settings_dict)
            if "default_tax_rate" in settings_dict:
                from decimal import Decimal, InvalidOperation
                percentage = Decimal(str(settings_dict["default_tax_rate"]))
                if not percentage.is_finite() or not 0 <= percentage <= 50:
                    raise ValueError("Sales tax must be between 0 and 50 percent.")
                settings_dict["default_tax_rate_format"] = "percent_v1"
                settings_dict["tax_rate_review_required"] = "0"
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
