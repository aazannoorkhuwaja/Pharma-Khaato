#!/usr/bin/env python3
"""Production-safe end-to-end business-flow verification.

This script intentionally uses the same isolated ``.demo-data`` database as the
presentation launcher. It can be run before a demo without touching normal
Pharma-Khaato data.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Importing demo_mode establishes PHARMA_KHAATO_DATA_DIR before core imports.
from scripts.demo_mode import (
    DEMO_ADMIN_PASSWORD,
    DEMO_ADMIN_USER,
    reset_demo_storage,
    seed_demo_database,
)


def test_flow() -> int:
    print("=" * 68)
    print("PHARMA-KHAATO DEMO / LAUNCH BUSINESS-FLOW VERIFICATION")
    print("=" * 68)

    reset_demo_storage()
    summary = seed_demo_database()

    from core.auth_service import login_user
    from core.cash_session_service import get_active_session, get_session_cash_summary
    from core.credit_query_service import credit_snapshot
    from core.inventory_service import search_products
    from core.readiness_service import run_readiness_checks
    from core.reports_service import get_daily_sales_report
    from core.return_service import get_sale_for_return

    print("[1/7] Authentication")
    user = login_user(DEMO_ADMIN_USER, DEMO_ADMIN_PASSWORD)
    assert user is not None, "Demo administrator login failed"
    admin_id = int(user[0])

    print("[2/7] Sellable inventory / indexed search")
    panadol = search_products("Panadol")
    assert panadol, "Panadol demo stock is not searchable"

    print("[3/7] Open cash shift and physical-drawer accounting")
    session = get_active_session(admin_id)
    assert session and session.get("status") == "OPEN", "Demo shift is not open"
    cash = get_session_cash_summary(session["id"])
    assert cash is not None and cash["expected_cash"] >= 5000.0, "Cash summary is invalid"
    assert cash["cash_sales"] > 0, "Cash sale is missing from drawer summary"
    assert cash["cash_credit_collections"] > 0, "Cash credit collection is missing"

    print("[4/7] Customer Credit history")
    credit = credit_snapshot("", limit=100)
    rows = credit.get("rows", []) if isinstance(credit, dict) else []
    assert rows, "Demo customer-credit ledger is empty"

    print("[5/7] Tender-aware reports")
    report = get_daily_sales_report()
    assert report and report.get("total_transactions", 0) >= 5, "Demo sales did not reach reports"

    print("[6/7] Return lookup")
    return_sale_id = summary["sale_ids"]["cash"]
    sale = get_sale_for_return(return_sale_id)
    assert sale and sale.get("lines"), "A seeded sale cannot be loaded for Returns"

    print("[7/7] Launch self-check")
    readiness = run_readiness_checks()
    assert readiness.get("ok"), "Readiness self-check failed"

    print("\nPASS — isolated demo business flow is ready.")
    print(f"Demo database: {summary['data_dir']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(test_flow())
    except Exception as exc:
        print(f"\nFAIL — {exc}", file=sys.stderr)
        raise
