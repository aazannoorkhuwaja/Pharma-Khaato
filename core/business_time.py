"""One explicit shop timezone for dates used in financial and expiry decisions."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ShopClockError(ValueError):
    """The configured business clock cannot be used safely."""


def business_timezone():
    name = os.environ.get("PHARMA_KHAATO_TIMEZONE", "Asia/Karachi")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ShopClockError(
            "Invalid shop timezone. Set PHARMA_KHAATO_TIMEZONE to a valid timezone "
            "such as Asia/Karachi, then restart Pharma Khaato. "
            "Database access and interrupted-restore recovery wait until the timezone is corrected."
        ) from exc


def business_now():
    return datetime.now(business_timezone())


def business_date():
    return business_now().date()
