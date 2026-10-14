"""Cheap process-local data revision tracking for cache-aware UI navigation.

Controllers bump domain revisions after successful mutations. The router records
which revisions a screen last rendered and only asks that screen to refresh when
one of its relevant domains changed (or its max-age expires).

This avoids re-running the same SQLite queries and rebuilding Qt tables every
single time a user clicks away and back, while still keeping business data fresh
after sales, stock changes, credit payments, refunds, and shift operations.
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Iterable

_LOCK = Lock()
_REVISIONS: dict[str, int] = defaultdict(int)


def touch(*domains: str) -> None:
    """Increment one or more logical data-domain revisions."""
    clean = {str(domain).strip().lower() for domain in domains if str(domain).strip()}
    if not clean:
        return
    with _LOCK:
        for domain in clean:
            _REVISIONS[domain] += 1


def snapshot(domains: Iterable[str]) -> tuple[tuple[str, int], ...]:
    """Return a stable, comparable snapshot for the requested domains."""
    clean = sorted({str(domain).strip().lower() for domain in domains if str(domain).strip()})
    with _LOCK:
        return tuple((domain, int(_REVISIONS.get(domain, 0))) for domain in clean)


def current(domain: str) -> int:
    key = str(domain or "").strip().lower()
    with _LOCK:
        return int(_REVISIONS.get(key, 0))
