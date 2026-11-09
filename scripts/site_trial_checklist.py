#!/usr/bin/env python3
"""Record on-site pharmacy acceptance results without accessing shop data.

Not a test runner. No database, patient record, printer, payment gateway or
scanner is accessed. A human must physically execute and attest each case.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CASES = (
    ("setup", "New installation and first owner sign-in"),
    ("upgrade", "Upgrade preserves previous shop and credentials"),
    ("cashier_role", "Cashier cannot enter owner-only settings/restore"),
    ("layout_1366", "1366x768 monitor at 100 percent: no clipped primary action"),
    ("layout_dpi", "Real Windows monitor at 125/150 percent scaling"),
    ("barcode_ean", "Physical scanner reads EAN-8/EAN-13, leading zero, pack codes"),
    ("barcode_rapid", "20 rapid consecutive physical scans without loss/duplicates"),
    ("barcode_bad", "Missing/ambiguous barcode never adds wrong medicine"),
    ("units", "Tablet/strip/box conversion matches counted stock"),
    ("expiry", "Expired, blocked and quarantined stock cannot be sold"),
    ("fefo", "Near-expiry valid batch is selected and independently verified"),
    ("last_unit", "Concurrent counters cannot oversell last stock unit"),
    ("cash_sale", "Cash sale, cash received/change, and drawer balance agree"),
    ("wallet", "Wallet/card tender correctly recorded (external confirmation separate)"),
    ("credit", "Credit customer sale and partial/full repayment reconcile"),
    ("discount", "Threshold discount requires manager approval"),
    ("hold", "Hold/restart/resume preserves cart without creating a sale"),
    ("printer_80", "Real 80mm receipt printed, aligned, readable, and complete"),
    ("printer_58", "Real 58mm receipt printed, aligned, readable, and complete"),
    ("printer_offline", "Disconnected/empty-paper printer leaves one saved sale"),
    ("reprint", "Reprinting one saved sale never creates a second sale"),
    ("returns", "Partial refund and returned-stock condition reconcile"),
    ("suppliers", "Supplier receiving/invoice/payment matches physical goods"),
    ("stock_count", "Physical stock count/correction is traceable"),
    ("shift_close", "Cash close expected/actual/difference match manual count"),
    ("reports", "Sales, returns, credit, payment mix and cash reports reconcile"),
    ("backup", "Backups saved outside primary computer and integrity-checked"),
    ("restore", "Restore works on a separate spare machine with matching totals"),
    ("lan_outage", "LAN counter disconnect blocks unsafe checkout and recovers"),
    ("restart", "Power-interruption simulation does not create duplicate sale"),
    ("update_rollback", "Update and recovery procedure validated on spare shop"),
    ("support", "Help/support process works without sharing patient/customer data"),
    ("training", "Two staff complete an unprompted routine bill within agreed target"),
    ("regulatory", "Qualified owner/adviser has reviewed local legal and tax requirements"),
)

ALLOWED = {"not_run", "pass", "fail", "blocked"}


def default_record():
    return {
        "kind": "human-site-acceptance",
        "version": 1,
        "site": "REPLACE WITH NON-SENSITIVE SHOP ALIAS",
        "application_commit": "RECORD TESTED COMMIT",
        "target_hardware": "RECORD MODEL/OS/PRINTER/SCANNER",
        "operator": "RECORD OPERATOR NAME LOCALLY",
        "reviewer": "RECORD SHOP OWNER/REVIEWER LOCALLY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "notice": "No live customer data, invoices, CNICs, passwords or patient info in this file.",
        "cases": {key: {"title": title, "status": "not_run", "evidence": "", "notes": ""}
                  for key, title in CASES},
    }


def load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = set(dict(CASES))
    if data.get("kind") != "human-site-acceptance" or set(data.get("cases", {})) != expected:
        raise ValueError("Not a valid/current Pharma-Khaato human site trial record.")
    return data


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".site-acceptance-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def evaluate(data):
    status_count = {status: sum(item["status"] == status for item in data["cases"].values())
                    for status in ALLOWED}
    ready = status_count["pass"] == len(CASES)
    print(f"Human site trial: {len(CASES)} cases; " +
          ", ".join(f"{k}={status_count[k]}" for k in ("pass", "fail", "blocked", "not_run")))
    for key, case in data["cases"].items():
        if case["status"] != "pass":
            print(f"  {case['status'].upper():7} {key}: {case['title']}")
    print("SITE TEST RESULT: " +
          ("ALL CASES RECORDED PASS — OWNER SIGN-OFF STILL REQUIRED" if ready
           else "NOT ACCEPTED / UNVERIFIED — DO NOT RELEASE TO LIVE COUNTER"))
    return 0 if ready else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--file", default="artifacts/site_acceptance.json")
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--init", action="store_true", help="Create an all-NOT_RUN acceptance worksheet")
    action.add_argument("--list", action="store_true", help="List IDs and criteria")
    action.add_argument("--evaluate", action="store_true", help="Show go/no-go status; nonzero if incomplete")
    action.add_argument("--record", metavar="CASE_ID", help="Record a result after physical test")
    p.add_argument("--status", choices=sorted(ALLOWED), help="Required with --record")
    p.add_argument("--evidence", default="", help="Non-sensitive evidence reference, e.g. photo filename")
    p.add_argument("--notes", default="", help="Avoid customer, invoice or patient identifiers")
    args = p.parse_args()
    path = Path(args.file)
    if args.list:
        for key, title in CASES:
            print(f"{key:18} {title}")
        return 0
    if args.init:
        if path.exists():
            p.error(f"Refusing to overwrite existing trial record: {path}")
        atomic_write(path, default_record())
        print(f"Created unverified on-site worksheet: {path}")
        return 0
    if not path.exists():
        p.error(f"No trial record found: {path}. First run --init.")
    data = load(path)
    if args.record:
        if args.record not in data["cases"]:
            p.error(f"Unknown test ID: {args.record}")
        if args.status is None:
            p.error("--status required for --record")
        data["cases"][args.record].update(
            status=args.status, evidence=args.evidence, notes=args.notes
        )
        data["last_recorded_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write(path, data)
        print(f"Recorded {args.record}: {args.status}. This is a human-attested result.")
        return 0
    return evaluate(data)


if __name__ == "__main__":
    raise SystemExit(main())
