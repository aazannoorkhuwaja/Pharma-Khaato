# Real-world readiness: 2.4.0 engineering build

This change targets a single computer, loose tablet/strip/box sales, and multiple local counters sharing one main shop computer. It is an engineering build pending shop acceptance, rather than a certification that every machine or workflow is error-free.

## Implemented safeguards

- Atomic checkout with explicit durable request identity, stock/price/expiry checks, immutable line values and saved receipt content. Retry returns the original committed sale.
- Canonical tax percentages with mandatory review for ambiguous legacy settings; cash tender and manager discount authorisation enforced by the backend.
- Base-unit stock with strip/box conversions, pack barcodes, month/day expiry, lot cost/sale prices, counted adjustments and blocked batches.
- Supplier invoices, free stock, balances, later payments and supplier return credits recorded atomically with stock/cash effects.
- Name-first customer accounts, optional phone/CNIC, account repayments, credit limits, statements and auditable repayment reversals.
- Counter-specific cash shifts and durable pending cash/stock/supplier/payment operations. Digital tenders stay outside the physical drawer.
- Idempotent returns and refunds, exact proportional line values, and separate gross sales, returns and net sales reporting.
- TLS shared-counter service with a trusted shop certificate, authenticated sessions, server-side actor/terminal permissions and mutation replay protection. No shared SQLite file.
- Restore validation/staging, backup-before-upgrade, interrupted-restore recovery, restart barrier, periodic backup snapshots and configurable external backup destination.
- Bounded background workers, paginated lists, minimal Qt runtime dependency and independent local printer preferences on counters.

## Automated evidence

The full source regression suite, isolated business-flow check, eight-screen offscreen check and Linux frozen-build smoke are run during integration. Observed results are recorded in [VALIDATION_2_4_0.md](VALIDATION_2_4_0.md). Tests exercise simulated failures and concurrent requests; they do not prove physical power-loss resilience or native hardware compatibility.

Reproduce source checks from the repository root:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q --show-capture=no
python scripts/demo_mode.py --no-launch
python scripts/test_gui_auto.py
python main.py --functional-smoke --headless
```

The demo scripts use `.demo-data` only. The functional smoke creates a temporary shop and deletes it when finished. For an installed build run `pharma_khaato --functional-smoke --headless`; it checks migrations, login, stock, cash, checkout replay, receipts, TLS certificate generation and eight screens without using shop records.

## Required shop acceptance

Record the build/checksum, Windows version, CPU/RAM, scanner and printer models, tester and date. Keep the previous working installation and verified backup available during the pilot.

1. **Native Windows install and upgrade:** install as an ordinary user, create a shop, upgrade with existing records, reboot, launch again, and verify data remains. Test that uninstall preserves shop data. Cloud Linux verification does not replace this.
2. **Printer:** check real 58/80 mm paper, margins, cutter, Urdu customer names, long medicine names, multiple pages and reprints. Unplug/reconnect during printing; verify a saved sale is not recreated. A spooler acknowledgement alone does not prove paper printed.
3. **Scanner:** scan rapid consecutive items, leading-zero codes and each pack barcode; verify one scan means one addition and typed searches still work.
4. **Drawer and shifts:** count opening cash; perform cash, Card, Easypaisa, JazzCash, credit collection, refund and supplier payment; count and close. Verify each counter's totals separately.
5. **Stock:** receive an invoice with two lots, strip/box conversions and free tablets; sell each unit, return a portion, block one lot, check expiry-day and month-only expiry. Verify counted balances against physical stock.
6. **Recovery:** on a spare shop, disconnect LAN during checkout, repayment, return, receiving and cash close. Reconnect and confirm the original operation exactly once. Test app termination and a controlled power interruption, then restore an external backup on a spare machine and reconcile records.
7. **Two counters:** attempt to buy the last stock simultaneously, use two separate shifts, change a staff password and verify the old session stops working. Confirm counters cannot work against their own empty local database while disconnected.
8. **Staff usability:** let a new cashier complete ten realistic bills, one held bill, a credit collection and a return without coaching. Record errors and time on the shop's lowest-spec computer.
9. **Owner sign-off:** verify opening stock, customer dues and supplier opening balances before switching over. Historic supplier opening balances need an agreed import/entry process; new invoice tracking alone does not reconstruct old debts.

## Current limits

- No offline independent counter sales, internet multi-branch synchronisation, full Urdu interface, clinical decision support, or automatic FBR integration is claimed.
- Unsubmitted carts need **Hold** to survive closing the app. Pending submitted operations are preserved locally; retain each counter's application-data folder during recovery.
- Main-computer operation requires stable LAN addressing, trusted certificate distribution and appropriate local firewall setup. A technician should perform initial multi-counter setup.
- Prescription flags identify products; qualified staff must check prescription and dispensing requirements. Tax rates and operational policies require owner review.
- No quantitative performance claim for low-end shop hardware is made from the cloud machine. Measure launch and common actions on the actual computer before rollout.
