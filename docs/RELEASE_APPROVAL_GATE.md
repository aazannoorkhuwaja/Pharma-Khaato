# Release approval evidence gate

The PySide6 and backend test suites establish **software regression confidence** only. A successful build is not proof that real pharmacy operations, barcode hardware, receipt printing, backup recovery or local compliance are safe.

The merged Balanced Counter UI is installed in `main`; high-DPI desktop sizing is tracked in PR #16. The application remains **not approved for unsupervised live pharmacy dispensing** until the on-site evidence is verified.

## Gate sequence

1. Build the exact tested candidate from a pinned Git SHA and version; copy it to a **spare** PC. Keep any active pharmacy's data and software untouched.
2. Using a pharmacy supervisor, perform every case in [PHARMACY_SITE_ACCEPTANCE.md](PHARMACY_SITE_ACCEPTANCE.md). Use a real 1366×768 Windows monitor at 100%, 125% and 150%, real 58/80 mm thermal printer, physical barcode scanner, two counters if supported, and actual backup restore on a second spare machine.
3. Write all case statuses, **non-sensitive evidence references**, exact version/SHA, hardware identity, supervisor identity, and signed local approval to an acceptance worksheet. Avoid customer names, prescriptions, invoices or other private records in GitHub.
4. Run the fail-closed local gate below. It returns exit code 2 when anything is missing, pending or blocked. **An all-pass JSON cannot prove authenticity**, so separately inspect original device results and the supervisor's signature.
5. Only then request a release publication decision. Existing CI release-build workflow creates a **draft** release, not an automatic public release.

```bash
python scripts/site_trial_checklist.py --init --file artifacts/site_acceptance.json
# The onsite supervisor records actual results after performing physical tests.
python scripts/site_trial_checklist.py --evaluate --file artifacts/site_acceptance.json
python scripts/release_acceptance_gate.py \
  --file artifacts/site_acceptance.json \
  --revision "$(git rev-parse HEAD)" \
  --version "$(python -c 'from config import ApplicationSettings; print(ApplicationSettings.APP_VERSION)')"
```

The `approval` section requires `decision: "approve_pilot"`, a real date, `supervisor_signature_reference`, and `legal_tax_review_reference`. Every 34-case status must be `pass`; critical hardware, cash, expiry, recovery and training cases must include non-sensitive evidence references. The exact tested commit and app version must match.

### Not yet completed

- Actual Windows high-DPI monitor verification and native font readability.
- Real 58mm/80mm receipt printout and disconnected-printer repeat sale workflow.
- USB/barcode-scanner 20-scan test on shop hardware.
- Cash/tender reconciliation, physical lot allocation/FEFO, LAN outage and last-stock contention.
- Restore on another machine, owner training and supervisory acceptance.
- Appropriate Pakistan/Sindh pharmacy, tax, data-privacy and business support review.

**Release state: blocked until evidence exists.** Do not claim 100% market readiness based on automated test counts.
