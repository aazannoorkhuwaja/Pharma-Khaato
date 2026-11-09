#!/usr/bin/env python3
"""Fail closed on missing on-site acceptance before a *human* release decision.

Runs locally against the non-sensitive 34-case site worksheet. Does not access
customer data, devices, or the pharmacy DB. A JSON worksheet can be forged;
this check enforces completeness, not the authenticity of a supervisor's signoff.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.site_trial_checklist import CASES, load

CRITICAL = (
    "layout_dpi", "barcode_rapid", "barcode_ean", "printer_80",
    "printer_58", "printer_offline", "reprint", "cash_sale",
    "shift_close", "reports", "backup", "restore", "lan_outage",
    "last_unit", "regulatory", "training", "expiry", "fefo",
)


def validate(record: dict, revision: str, version: str) -> list[str]:
    blockers: list[str] = []
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        blockers.append("Candidate revision must be a full Git commit SHA.")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        blockers.append("Version must be major.minor.patch.")
    if record.get("kind") != "human-site-acceptance":
        return blockers + ["Incorrect site acceptance worksheet type."]
    if record.get("application_commit") != revision:
        blockers.append("Tested revision does not match release candidate.")
    if record.get("application_version") != version:
        blockers.append("Tested version does not match release candidate.")
    for key in ("site", "target_hardware", "operator", "reviewer"):
        val = str(record.get(key) or "").strip()
        if not val or val.upper().startswith(("RECORD ", "REPLACE ")):
            blockers.append(f"Missing onsite metadata: {key}.")
    cases = record.get("cases", {})
    if not isinstance(cases, dict) or set(cases) != {key for key, _ in CASES}:
        blockers.append("Site worksheet missing required cases.")
    else:
        for key, _ in CASES:
            case = cases[key]
            if not isinstance(case, dict) or case.get("status") != "pass":
                blockers.append(f"Site case not passed: {key}.")
            if key in CRITICAL and not str(case.get("evidence") or "").strip():
                blockers.append(f"Critical case has no evidence reference: {key}.")
    approval = record.get("approval") or {}
    if approval.get("decision") != "approve_pilot":
        blockers.append("Explicit supervised pilot approval is missing.")
    for key in ("date", "supervisor_signature_reference", "legal_tax_review_reference"):
        if not str(approval.get(key) or "").strip():
            blockers.append(f"Approval is missing {key}.")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        data = load(args.file)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print("BLOCKED: no valid on-site acceptance record:", exc)
        return 2
    errors = validate(data, args.revision, args.version)
    for message in errors:
        print("BLOCKED:", message)
    if errors:
        print(f"Release evidence gate: NOT APPROVED ({len(errors)} blockers)")
        return 2
    print("Evidence fields complete for this exact revision and version.")
    print("Authenticity and final authorization must still be verified by a human supervisor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
