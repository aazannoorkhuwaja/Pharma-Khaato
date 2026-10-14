import os
import sys
import unittest
import subprocess

def run_suite(name, script_path):
    print(f"\n============================================================")
    print(f"  EXECUTING CROSS-TEST FOR {name.upper()}")
    print(f"============================================================")
    res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
    return res.returncode == 0

def main():
    print("\n" + "=" * 60)
    print(" 🏥 PHARMA-KHAATO MASTER PRODUCTION CROSS-TESTING SUITE ")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    suites = [
        ("Phase 1 — Data Architecture & Settings", os.path.join(base_dir, "test_phase1.py")),
        ("Phase 2 — POS Engine & Barcode Hardening", os.path.join(base_dir, "test_phase2.py")),
        ("Phase 3 — FEFO Expiry & Cash Session Management", os.path.join(base_dir, "test_phase3.py")),
        ("Phase 4 — Receipts, Khatoo & Reporting Engine", os.path.join(base_dir, "test_phase4.py")),
        ("Phase G — Native POS Billing Screen", os.path.join(base_dir, "test_phase_g.py")),
        ("Phase H — Inventory & Batch Management", os.path.join(base_dir, "test_phase_h.py")),
        ("Phase I — Customer & Khatoo Ledger", os.path.join(base_dir, "test_phase_i.py")),
        ("Phase J — Cash Session Register", os.path.join(base_dir, "test_phase_j.py")),
        ("Phase K — Executive Reports & System Settings", os.path.join(base_dir, "test_phase_k.py")),
        ("Phase L — Final System Integration & Acceptance", os.path.join(base_dir, "test_phase_l.py")),
        ("Security & Configuration Standards", os.path.join(base_dir, "test_security.py")),
        ("Schema Migration & Backward Compatibility", os.path.join(base_dir, "test_migration.py")),
        ("Resource & Connection Leak Monitoring", os.path.join(base_dir, "test_leaks.py")),
        ("End-To-End System Integration Flow", os.path.join(base_dir, "test_flow.py")),
    ]

    results = []
    for name, path in suites:
        passed = run_suite(name, path)
        results.append((name, passed))

    print("\n" + "=" * 60)
    print(" 📊 MASTER CROSS-TESTING SUMMARY RESULT ")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} :: {name}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print(" 🎉 ALL CROSS-VERIFICATION SUITES PASSED PERFECTLY!")
        sys.exit(0)
    else:
        print(" ❌ MASTER CROSS-TESTING ENCOUNTERED FAILURES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
