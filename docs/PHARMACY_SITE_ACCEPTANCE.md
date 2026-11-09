# Pharma-Khaato physical hardware and pharmacy-site acceptance

**Status:** NOT RUN on any real pharmacy or physical device. This worksheet is an operational handoff. Headless GitHub screenshots, mock spooler tests and an isolated demo do **not** substitute for operator sign-off.

## Scope and safety

1. Use a **spare computer and a practice shop**. Never reset/import demo data over an operational shop. Record the tested app version, Git commit, PC, Windows/Linux version, resolution, Windows scaling, printer model/driver, barcode scanner model, and LAN topology.
2. Before any upgrade or real entry, **create and successfully restore** a backup on a separate computer. Preserve a second external backup. Keep the existing POS and paper records available until the owner accepts the pilot.
3. Use synthetic customer names, barcodes and invoices. No patient identity, real CNIC, passwords, or private medicine history belongs in screenshots or public GitHub issues.
4. Do **not** conduct live patient dispensing, real payment collection, or legally regulated medicine sale as an experiment; a qualified pharmacy owner/supervisor must oversee a real deployment decision.
5. Hardware checks must use real installed devices on the target shop computer. CI can emulate keyboard input and failures but cannot prove barcode-scanner read rate or printer feed/driver reliability.

## Automated gates currently available

- `python -m pytest -q`: service, UI, backend authorization, credit, receipt snapshots, transactional sale and retry tests, simulated keyboard-wedge scanner and printer disconnect.
- `python scripts/test_gui_auto.py`: legacy native Qt offscreen screenshot smoke with demo dataset.
- `python scripts/ui_acceptance_matrix.py --strict`: eight major screens at 900×600, 1024×768, 1366×768 and 1920×1080 logical pixels; light/dark themes, standard/compact density, 125/150% **font** scale, plus select workflow sub-tabs. Uploads screenshots, overview contact sheets and `manifest.json` from Windows/Linux hosted runners at simulated Qt device ratios.
- `python scripts/demo_mode.py --no-launch` and `python scripts/test_flow.py`: isolated demo with stock, shifts, credit and sales flow.

**Not proven by automation:** physical Windows scaling on a 1366×768 monitor, scanner hardware, thermal paper alignment, 58/80 mm output, cash handling, shop Wi-Fi outage, real-device backup/restore, staff training or local regulatory compliance.

### Critical physical display limitation to test

At **1366×768 physical pixels with Windows scaling at 150%**, a Qt app sees roughly **911×512 logical pixels** before taskbar space, <!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:d70e91b4b862d2ed0203bd462fd539295fd5eb8b77231724ec1a96cc196f5018 -->

and the current minimum application height is **440 logical pixels**. The layout adapts to short windows, but actual taskbar space, fonts and driver scaling still need verification on a Windows workstation.

<!-- /coderabbit-ai-generated:v1 --> Do not interpret headless `QT_SCALE_FACTOR=1.5` screenshots of a 1366×768 **logical** window as proof that this physical configuration works.

## Actual on-site test protocol

Use at least two operators (one experienced cashier and one novice), a supervisor, and a spare shop workstation. Time the unprompted task and record whether the correct result appeared in the database, receipt, dashboard and cash drawer.

| Stage | Practical checks | Pass requirements |
| --- | --- | --- |
| Installation | First owner setup, clean restart, install update, separate cashier login | No loss of settings or data; correct permissions |
| Resolution/DPI | 1366×768 at Windows 100/125/150%, plus 1920×1080 | No inaccessible checkout/total, focus, overlapping text or orphan controls |
| Scanner | EAN-8/EAN-13, leading zeros, unit barcodes, repeated 20 scans, ambiguous/missing code | Every scan maps to the correct medicine/unit once; no phantom stock |
| Receipts | 58/80 mm installed drivers; paper width, name wrap, taxes/totals, Unicode; disconnect printer | Saved sale remains one committed sale; reprint works without new sale |
| POS | Cash, card, wallets, credit, discounts, hold/recall, refunds, stale stock | Totals, customer balances and on-hand stock independently reconcile |
| Receiving | Supplier invoice, changed lot price, pack conversion, expiry dates, returns | Physical counts, FEFO and payable balances match |
| Cash | Opening float, cash sale, refunds, manual cash in/out, shift close | Expected and actual amount plus variance are correctly explained |
| LAN | Two active counters, simultaneous last strip, outage while submitting and reconnect | No oversell, duplicate checkout or unrecognized commit |
| Recovery | Power loss in a disposable shop, restore elsewhere, update/rollback rehearsal | Database remains consistent; all historical sales and balances preserved |
| Reports | Date boundary, refunds, payments, credit collection, supplier dues | Financial reports reconcile with independently checked transaction totals |
| Privacy/operations | Screen permissions, redacted support bundles, employee handoff, owner training | No unauthorized actions; operator understands recovery without recharging |

## Recording and sign-off

Create a JSON worksheet (all statuses start as `not_run`):

```bash
python scripts/site_trial_checklist.py --init --file artifacts/site_acceptance.json
python scripts/site_trial_checklist.py --list
python scripts/site_trial_checklist.py --record barcode_rapid --status pass --evidence "scanner-test-1.jpg" --notes "20 scans; 20 correctly recorded" --file artifacts/site_acceptance.json
python scripts/site_trial_checklist.py --evaluate --file artifacts/site_acceptance.json
```

Allowed statuses: `not_run`, `pass`, `fail`, `blocked`. Recording is human-attested; the script never accesses a shop database or printer. `--evaluate` returns nonzero unless **all 34 checks** pass; it does not issue regulatory certification. Never attach unredacted trial JSON/evidence to a public issue.

### Final supervisor decision (complete after real testing)

- Tested exact Git commit / version: ____________________
- OS / laptop / physical display / DPI: ____________________
- Scanner model and driver: ____________________
- 58mm/80mm printer model, paper and driver: ____________________
- Shop alias (non-sensitive): ____________________
- Recorded issue links and remediation: ____________________
- Owner / qualified supervisor: ____________________
- Date: ____________________
- Decision: **APPROVE PILOT / BLOCK / REQUEST FIXES** (circle one)
- Supervisor signature: ____________________

**Release criteria:** zero unresolved financial integrity, dispensing, permissions or recovery blockers; actual scanner and printer tested, verified external restore, trained staff and owner approval. Commercial/legal readiness requires separate qualified review.

## Interpretation

A completed GitHub UI acceptance workflow shows only that Qt rendered, critical visible anchors were within application bounds, and screenshots were captured using disposable sample data. It cannot independently certify visual taste, full text clipping, monitor hardware DPI, printer quality or real pharmacy operations. Inspect all produced image contact sheets before any merge.
