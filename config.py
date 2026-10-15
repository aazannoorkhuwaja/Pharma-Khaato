import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ApplicationSettings:
    """Central product identity and runtime metadata.

    Keep user-facing product naming here so the executable, installer, About
    dialog, support bundle and documentation all report the same identity.
    Filesystem/package identifiers intentionally remain stable for upgrades.
    """

    APP_NAME = "Pharma-Khaato"
    DISPLAY_NAME = "Pharma Khaato"
    APP_VERSION = "2.3.1"
    APP_ID = "com.pharmakhaato.desktop"
    ORGANIZATION = "Pharma Khaato"
    PRODUCT_TAGLINE = "Pharmacy POS & Inventory Management"
    PRODUCT_DESCRIPTION = (
        "Offline-first pharmacy billing, batch inventory, customer credit, "
        "cash shifts, returns, reports and recovery."
    )
    DATA_NOTICE = "Business data is stored locally on this computer unless you export or back it up."
    SUPPORT_EMAIL = os.getenv("PHARMA_KHAATO_SUPPORT_EMAIL", "").strip()

    @classmethod
    def version_label(cls) -> str:
        return f"{cls.DISPLAY_NAME} {cls.APP_VERSION}"


class PharmacySettings:
    """Configurable Pharmacy Profile and Statutory Regulatory Data."""

    NAME = os.getenv("PHARMACY_NAME", "Pharma-Khaato Pharmacy")
    SLOGAN = os.getenv("PHARMACY_SLOGAN", "Pharmacy & Surgical Care")
    ADDRESS = os.getenv("PHARMACY_ADDRESS", "Main Healthcare Boulevard")
    PHONE = os.getenv("PHARMACY_PHONE", "Customer Care Line")
    EMAIL = os.getenv("PHARMACY_EMAIL", "info@pharmakhaato.com")
    LICENSE_NUMBER = os.getenv("PHARMACY_LICENSE", "NOT_CONFIGURED")
    NTN_NUMBER = os.getenv("PHARMACY_NTN", "NOT_CONFIGURED")
    RECEIPT_FOOTER = os.getenv("PHARMACY_FOOTER", "Thank you for trusting Pharma-Khaato.")

    # Tax & Business Logic Defaults
    TAX_RATE = float(os.getenv("TAX_RATE", 0.10))
    DEFAULT_MIN_STOCK = int(os.getenv("DEFAULT_MIN_STOCK", 10))
    NEAR_EXPIRY_DAYS = int(os.getenv("NEAR_EXPIRY_DAYS", 30))


# Backward compatibility alias
Config = ApplicationSettings
