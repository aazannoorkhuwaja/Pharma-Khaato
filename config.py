import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class ApplicationSettings:
    """Centralized application constants and environment settings."""
    APP_NAME = "Pharma-Khaato"
    APP_VERSION = "2.3.1"

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
