"""One explicit shop timezone for dates used in financial and expiry decisions."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo


def business_now():
    return datetime.now(ZoneInfo(os.environ.get("PHARMA_KHAATO_TIMEZONE", "Asia/Karachi")))


def business_date():
    return business_now().date()
