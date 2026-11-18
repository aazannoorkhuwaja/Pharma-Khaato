# Target-machine operator acceptance

Local evidence covers Linux offscreen rendering and widget behavior. It does not establish Windows layout, assistive-technology interoperability, physical printing/scanning, or exact visual equivalence to the supplied UI sample ZIP.

Record OS version, display resolution/DPI, Qt/runtime, application commit and installer hash, operator/reviewer, device model/firmware/driver and test date. Complete the existing `scripts/site_trial_checklist.py` worksheet plus the release evidence manifest; attach redacted screenshots and measured results.

| Area | Required exercise and pass condition |
|---|---|
| Windows/Linux layouts | 1024×768, 1280×720 and 1366×768 at supported 100/125/150/200% scaling; expanded text and long medicine/customer names. Totals, tender/change, error text and primary actions remain visible. Native Windows font metrics must be tested on Windows. |
| Reference UI | Compare every principal screen against the supplied samples side by side at matching dimensions; record deviations and owner acceptance. Keep the financial and medicine-state safeguards visible. The sample ZIP remains unchanged. |
| Keyboard | Complete login, product search, explicit lot selection, quantity/unit edit, cash/card/credit checkout, hold/resume, return, cash close and logout without a mouse. Verify shortcut conflicts, tab order, visible focus, Escape behavior and modal focus return. |
| Screen readers | Use NVDA on Windows and Orca on Linux. Check accessible names, form buddies, table headers/values, lot/expiry/prices, error/status announcements, required fields, focus and disabled states. Automatic widget names alone are insufficient. |
| UI states | Trigger empty results, permission denial, failed load, offline counter, unknown transaction outcome and recovery failure. Errors must remain distinguishable from zero data or success; retry must preserve request identity. |
| Mixed-price lots | Receive two lots of the same product at different prices/expiries. Search and scan, select each lot explicitly and verify separate cart lines, requested quantities, receipt prices and stock deduction. Exhausting a chosen lot must not consume another silently. |
| Medicine safeguards | Restricted medicine remains blocked at UI and service. Expired, malformed-expiry, quarantined and recalled batches cannot sell. An invalid report must show failure, not an empty safe-stock list. |
| Settings and staff | Delay settings reads/saves and staff operations; typing/navigation stays responsive. Preserve unsaved edits. Deactivate an employee and confirm existing sessions and unused manager approvals stop working. |
| Scanner | Record exact USB/HID model and configured suffix. Test EAN/Code128 and supported internal codes; rapid repeat scans, unknown/ambiguous codes, strip/box codes, focus outside search, unplug/reconnect, and no duplicate checkout. Verify physical quantities against pack conversion. |
| Printer | Record exact 58/80 mm model and driver. Verify wrapping, totals, tender/change, cut/margins, Unicode names, long receipts and visible reprint marking. Unplug, paper-out, spooler stop/restart and reconnect after commit: sale remains saved once and reprint does not change stock/cash. |
| Cash drawer | If supported by the deployment's printer/driver, verify only approved events open the drawer and denied/failed transactions do not. Do not claim compatibility without the actual device. |
| Recovery window | Start through installed OS shortcut/action without Python. Wrong credentials/passphrase, tampered/truncated bundle, existing destination and another active host fail safely. Close/Escape cannot interrupt active work. A successful recovery stays offline until reconciliation. |
| Pilot | Named cashier completes an observed trading-day rehearsal on fixtures, including shift boundaries and outage recovery. Reconcile sales, credit, supplier balance, stock and cash. Record training and escalation acceptance. |

Failure in financial integrity, medicine eligibility, authorization, unresolved transaction outcomes or recoverability blocks pilot promotion. Cosmetic approval cannot waive those failures.
