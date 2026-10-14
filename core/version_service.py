"""
version_service — lightweight release update check.

Checks GitHub Releases for a newer version. Never blocks the UI thread:
call from a background worker; failures are silent (offline pharmacies are
the primary deployment target).
"""

import json
import urllib.request

from core.logger import get_logger

logger = get_logger("PharmaKhaatoVersion")

CURRENT_VERSION = (2, 2, 0)
VERSION_CHECK_URL = (
    "https://api.github.com/repos/aazannoorkhuwaja/Pharma-Khaato/releases/latest"
)


def _parse_version(tag: str):
    """'v2.1.0' -> (2, 1, 0). Non-numeric segments are ignored."""
    parts = []
    for chunk in tag.lstrip("vV").split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0, 0, 0)


def check_for_updates(timeout: float = 3.0):
    """
    Returns dict with update info when a newer release exists, else None.
    All network/parse failures return None silently.
    """
    try:
        req = urllib.request.Request(
            VERSION_CHECK_URL,
            headers={"User-Agent": "PharmaKhaato-POS-Updater", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        latest = _parse_version(data.get("tag_name", ""))
        if latest > CURRENT_VERSION:
            return {
                "has_update": True,
                "current_version": ".".join(map(str, CURRENT_VERSION)),
                "latest_version": ".".join(map(str, latest)),
                "release_notes": data.get("body", ""),
                "download_url": data.get("html_url", ""),
            }
    except Exception as e:
        logger.info(f"Version check skipped (offline or unreachable): {e}")
    return None
