# Pharma Khaato 2.4.1 — launch candidate evidence

Recorded on 27 October 2026 from a Linux cloud workspace: Python 3.12.3,
PySide6/Qt 6.7.2, Qt `offscreen` platform, no display, no GPU.

This is an engineering record. It says what was run and what it returned. It is
**not** native Windows, printer, scanner, cash-drawer or owner acceptance — those
remain open in [Real-world readiness](REAL_WORLD_READINESS.md).

## Verification record

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Full source regression suite | `pytest -q` | **269 passed** in 62.3 s (exit 0) |
| 2 | Database migration suite | `python scripts/test_migration.py` | **5 passed**, exit 0 |
| 3 | Backend security suite | `python scripts/test_security.py` | **11 passed**, exit 0 |
| 4 | Layout / design-token audit | `python scripts/ui_audit.py` | all 6 checks PASS |
| 5 | Isolated business flow | `python scripts/test_flow.py` | 7/7 stages PASS |
| 6 | Offscreen screen check | `python scripts/test_gui_auto.py` | all 8 screens opened |
| 7 | Launch self-check, empty shop | `python main.py --self-check --headless` | **READY** (exit 0) |
| 8 | Disposable installed-shop smoke | `python main.py --functional-smoke --headless` | `{"ok": true, "version": "2.4.1"}` |
| 9 | Compilation of every package | `python -m compileall` | exit 0 |

Checks 2 and 3 were **red at the committed `main` head** before this candidate.
Evidence for that baseline was taken from a clean `git archive HEAD` copy: the
migration script failed with `no such column: p.brand_name` and the security
suite reported 3 failures. Both are now green because the scripts were repaired,
not because the assertions were dropped — see "Script repairs" below.

## Live shared-counter check

The shop server was started against a disposable shop
(`python scripts/run_shop_server.py --data-dir .demo-data`), then exercised over
its real TLS socket:

| Probe | Observed |
|---|---|
| `POST /v1/status` (unauthenticated) | `200` → `{"ready": true, "configured": true, "protocol": 1}` |
| TLS negotiation | `TLSv1.3`, cipher `TLS_AES_256_GCM_SHA384`, shop certificate `CN = Pharma Khaato Shop` |
| Login, wrong password | `200` with `{"result": null}`; no token issued, `Shop_Session` rows `0`, lockout counter incremented |
| Login, unknown staff | `200` with `{"result": null}` |
| Authenticated business call | `InventoryModel.search_products("Panadol")` returned live product rows over TLS |
| Reuse a logged-out token | `401` "Your shop sign-in has expired. Sign in again." |
| Forged session token | `401` (same) |
| Wrong content type | `415` "Use the shop application to connect." |

A wrong password is refused by the server, not merely by the client: the
response body is `null`, no session row is written, and any follow-up call is
rejected. The earlier note that a wrong password was "accepted" was a mistake in
a throwaway probe script, which treated "no exception" as success; the correct
client API returns `None`.

## Correctness changes in this candidate

1. **One money quantizer.** `core/money.py` is now the single definition of the
   quantum (`0.01`, `ROUND_HALF_UP`); report, drawer, receipt, ledger and
   repayment helpers delegate to it. `tests/test_money_and_audit_integrity.py`
   proves that `0.1 + 0.2` and a 3,000-line float aggregate both land on the
   exact total, and that no two helpers can disagree by a cent.
2. **Audit rows carry shop time.** `core/audit_service.py` used the workstation's
   local clock while cash-shift events in the same `Audit_Log` table used shop
   time, so the two could not be ordered together. Receipt and print timestamps
   now fall back to shop time as well.
3. **A missing base schema fails loudly.** A packaged build without
   `schema_sqlite.sql` previously produced a database with no tables; it now
   stops with an operator-facing message.
4. **Replayed migrations are visible.** A statement colliding with an existing
   column or object is tolerated for the additive case only, and is now logged at
   warning level (it was hidden at debug level), with a count reported at the end
   of the migration run.
5. **Obsolete MySQL-era code removed** from the SQLite connection layer: the
   `CURDATE()` / `DATE_ADD` / `FOR UPDATE` rewrites, the duplicated branch, the
   unused imports, and an unbounded statement cache.

## Script repairs

* `scripts/test_migration.py` simulated a legacy database containing only three
  tables. That premise is no longer supported — migration `012` indexes a column
  the shipped base schema provides — so the script itself failed at `012` on
  `main`. It now verifies the supported upgrade path against a disposable data
  folder: ordered application of every migration, survival of historical stock,
  staff and customer rows, a verified `quick_check` recovery point written before
  the first change, a second run that is a no-op, and schema equality with a
  fresh install.
* `scripts/test_security.py` ran against the **owner's real application-data
  folder** and performed a real backup *and restore* there; it also depended on
  retired APIs and stale message wording, so it failed at `main`. It now runs
  entirely inside a temporary shop, and its expectations match the current
  contract, including an oversized-repayment bound that was not covered before.

## Repository hygiene

Removed MySQL/XAMPP-era artifacts that no longer had any code reference:
`schema.sql`, `salesman_app.py`, `database/` (drawSQL export and `xampp.sh`),
five `scripts/test_track*_verification.py` files, and two superseded documents
(`docs/AUDIT_REPORT.md`, `docs/PY_SIDE6_MIGRATION_AUDIT.md`). The
database documentation now describes the shipped schema ordering and money
representation instead of a MySQL design.

## Known limitations carried by this candidate

* **Migrations cannot build a database from nothing.** `schema_sqlite.sql` is the
  supported baseline; migration `012` indexes `Products.brand_name`, which no
  migration creates. A shop database older than that baseline cannot be upgraded
  by this catalog. Making the catalog self-sufficient is scheduled for 3.0 and
  cannot be done by renumbering migrations already applied on live shops.
* **Sale, credit, cash and refund columns still store `REAL`.** They are exact in
  practice because every value is quantized to two places and every aggregate is
  re-quantized, but a move to integer minor units (as the supplier subsystem
  already uses) is a destructive change staged for 3.0.
* **No native acceptance.** Windows installer and signing, Ubuntu CI packaging,
  the receipt printer, the barcode scanner and the cash drawer are untested here
  and remain **Pending** in the acceptance record.
* **A bare Linux box needs Qt runtime libraries** (`libEGL`, `libxkbcommon`,
  `fontconfig`) before the offscreen checks can run; their absence shows up as an
  import failure at collection time, not as a test failure.

## How to reproduce

```bash
python -m pytest -q --show-capture=no
python scripts/test_migration.py
python scripts/test_security.py
python scripts/ui_audit.py
python scripts/test_flow.py
python scripts/test_gui_auto.py
python main.py --self-check --headless
python main.py --functional-smoke --headless --smoke-report report.json
```

Every check above uses a temporary or `.demo-data` shop. None of them read,
back up or restore an owner's records.
