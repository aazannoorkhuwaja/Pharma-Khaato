# UI and UX audit

Audit evidence collected: 2026-11-10; reports finalized: 2026-11-11. Phase 1: analysis and documentation only.

Baseline: local `ui/reference-replica`, commit `1dd242cebae3ca792750fc8dc91f03b84a7705ec`, matching the GitHub branch at inspection. GitHub `main` was `1fc56654c5a69ae62525a13b17c6235568f6eee6`; findings target the audited branch, not an assertion that main has identical UI. No application code, live database, merge, deployment, or release changes were made.

Evidence labels: **Reproduced** = observed in a disposable database or recorded exact-commit CI; **Source-confirmed** = reachable behavior established by code inspection; **Risk** = plausible consequence requiring a targeted experiment; **Unverified** = missing acceptance evidence. Severity reflects business impact, not exploitability alone. Complexity: S = 1–2 engineering days; M = 3–5; L = 1–2 weeks; XL = multiple weeks. Estimates exclude independent acceptance, regulatory review and rollout; overlapping fixes must not simply be summed.

## UI assessment and runtime evidence

The application uses native PySide6 screens, responsive layout rules, shortcuts, cart/session state and an asynchronous task runner. Reviewed areas include POS, inventory/batches, customers/credit, cash, returns, suppliers, reports, settings, login and recovery flows. This audit did not establish exact visual equivalence to the previously supplied sample ZIP, manually exercise a Windows desktop, or certify assistive-technology usability.

## U01 — Checkout total-placement acceptance test fails

- **Severity / impact:** High — amount visibility at payment confirmation is a financial usability gate.
- **Evidence status:** Reproduced in exact-commit CI
- **Location:** [ui/screens/pos_screen.py:522](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/pos_screen.py#L522); [tests/test_recording_review.py:102](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/tests/test_recording_review.py#L102).
- **Evidence:** Ubuntu and Windows Python 3.12 job logs each show 1 failed / 327 passed: test_total_and_change_stay_with_checkout_and_customer_id_stays_internal. At 1100×650, lbl_total is inside the scroll area contrary to the established acceptance assertion. This proves a layout contract failure, not an observed incorrect charge.
- **Reproduction / verification:** Run the named test with pytest-qt installed; inspect total, change and checkout visibility when the cart/summary scrolls.
- **Recommended correction:** Keep authoritative total/change and checkout together and visible at supported sizes; review the requirement with a cashier before changing the test.
- **Regression tests needed:** 1100×650 and minimum supported window; long cart; large fonts; DPI 100–150%; keyboard checkout; every payment method and unknown pending outcome.
- **Implementation complexity:** M.

## U02 — Windows shortcut legend clips at supported scenarios

- **Severity / impact:** Medium — operators lose discoverable keyboard guidance.
- **Evidence status:** Reproduced in exact-commit UI acceptance CI
- **Location:** [ui/screens/pos_screen.py:522](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/pos_screen.py#L522); [.github/workflows/ui-acceptance.yml:20](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/.github/workflows/ui-acceptance.yml#L20).
- **Evidence:** All three Windows scale jobs failed while all three Ubuntu scale jobs passed. Inspected Windows 1.5 log reports shortcut legend clipped for counter_1366/pos, dark_1366/pos and compact_1366/pos (80 captures, 10 scenarios, 8 screens).
- **Reproduction / verification:** Run the workflow matrix on Windows at 1.0/1.25/1.5; inspect screenshot artifacts and measured clipping.
- **Recommended correction:** Let legend wrap/reflow using measured font metrics, with consistent focus and shortcut behavior.
- **Regression tests needed:** All matrix scenarios, translated/long strings, high contrast, keyboard-only use and screenshot review.
- **Implementation complexity:** S.

## U03 — Settings operations can block the GUI thread

- **Severity / impact:** Medium — network delays can freeze configuration and staff-management interactions.
- **Evidence status:** Source-confirmed synchronous calls; freeze duration not benchmarked
- **Location:** [ui/screens/settings_screen.py:407](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/settings_screen.py#L407); [ui/screens/settings_screen.py:487](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/settings_screen.py#L487); [ui/screens/settings_screen.py:840](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/settings_screen.py#L840).
- **Evidence:** Settings construction/load/save and staff actions perform service calls synchronously. LAN timeout/retry budgets can turn these into visibly long stalls.
- **Reproduction / verification:** Use a disposable delayed/unreachable LAN host and open/save settings while observing repaint and input handling.
- **Recommended correction:** Move remote work to the existing asynchronous runner; show busy/error states, prevent duplicate mutation, and preserve unsaved input.
- **Regression tests needed:** Timeout/disconnect/reconnect; repeated click; navigate away mid-request; stale response; authorization failure; focus restoration and retry.
- **Implementation complexity:** M.

## U04 — Refund preview differs from committed refund

- **Severity / impact:** Medium — confirmation presents an incorrect amount.
- **Evidence status:** Reproduced
- **Location:** [ui/screens/returns_screen.py:299](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/returns_screen.py#L299); [core/return_service.py:102](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/return_service.py#L102); [core/return_service.py:242](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/return_service.py#L242).
- **Evidence:** A three-unit box totaling 1.00 returned as two base units previews 0.66, while the committed refund is 0.67. UI uses rounded unit price; backend allocates from line subtotal.
- **Reproduction / verification:** Run PREVIEW_MISMATCH in the disposable probe appendix.
- **Recommended correction:** Use one authoritative quote/allocation routine for preview and commit, with a version/revalidation check and clear explanation if state changed.
- **Regression tests needed:** Fractional pack prices, discounts/tax, prior partial returns, split tenders and concurrent return; displayed amount equals committed receipt.
- **Implementation complexity:** M.

## U05 — Multiple lot price groups lack a complete checkout selection flow

- **Severity / impact:** Medium — valid stock can be difficult to sell without confusing price changes.
- **Evidence status:** Source-confirmed workflow gap; operator acceptance untested
- **Location:** [core/product_search_service.py:19](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/product_search_service.py#L19); [ui/screens/pos_screen.py:770](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/pos_screen.py#L770); [ui/app/state/session_state.py:56](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/app/state/session_state.py#L56).
- **Evidence:** Search chooses the earliest sellable lot while allocation restricts compatible prices. Cart merging by product/unit and absence of a complete alternate-price lot selector can leave the user unable to satisfy a request spanning differently priced stock.
- **Reproduction / verification:** Create two FEFO lots with different prices, request more than the first lot quantity, and inspect rejection/recovery flow.
- **Recommended correction:** Expose price groups or split quoted FEFO allocations into explicit lines; show batch/expiry and total before confirmation.
- **Regression tests needed:** Mixed prices/MRPs, exhausted first lot, stale cart, expired second lot, barcode packs and user cancellation.
- **Implementation complexity:** L.

## U06 — Some medicine-monitoring failures look like empty results

- **Severity / impact:** High risk — a database failure may be mistaken for no expired or reorder stock.
- **Evidence status:** Source-confirmed error masking
- **Location:** [core/reports_service.py:142](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/reports_service.py#L142); [core/reports_service.py:176](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/reports_service.py#L176); [core/inventory_service.py:504](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/core/inventory_service.py#L504).
- **Evidence:** Several report queries catch exceptions and return an empty list, indistinguishable from a successful empty result to callers.
- **Reproduction / verification:** Inject a query failure in a disposable test and observe the rendered result/state.
- **Recommended correction:** Return explicit error results, retain last-good data with stale labeling, and show retry/support details without claiming zero alerts.
- **Regression tests needed:** Database locked/corrupt/missing object; LAN disconnect; genuinely empty stock; retry success; inaccessible details and loading state.
- **Implementation complexity:** M.

## U07 — Accessibility needs explicit widget metadata and manual validation

- **Severity / impact:** Medium — assistive-technology or keyboard users may not complete tasks reliably.
- **Evidence status:** Source-confirmed metadata gap; end-user impact unverified
- **Location:** [ui/screens/batches_screen.py:36](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/screens/batches_screen.py#L36).
- **Evidence:** Batch filter labels and combo boxes do not consistently establish accessible naming/buddy relationships. Automated geometry checks cannot establish screen-reader behavior or complete focus usability.
- **Reproduction / verification:** Inspect accessibility trees and tab order on all dialogs; exercise sales/returns with NVDA on Windows and Orca on Linux.
- **Recommended correction:** Add meaningful names/buddies, predictable focus/error announcements and keyboard paths; verify contrast and scaling under actual OS themes.
- **Regression tests needed:** Screen readers, keyboard-only sale/refund, disabled/busy/error states, 200% text, focus after dialogs, shortcuts without typing conflicts.
- **Implementation complexity:** L.

## U08 — Dormant async worker module cannot import

- **Severity / impact:** Low — future reuse of the module fails immediately.
- **Evidence status:** Reproduced; active async runner is separate
- **Location:** [ui/app/state/async_worker.py:1](https://github.com/aazannoorkhuwaja/Pharma-Khaato/blob/1dd242cebae3ca792750fc8dc91f03b84a7705ec/ui/app/state/async_worker.py#L1).
- **Evidence:** ImportError: cannot import name Runnable from PySide6.QtCore. This does not establish a current application startup failure.
- **Reproduction / verification:** Import ui.app.state.async_worker using the audited local runtime.
- **Recommended correction:** Remove obsolete module or correct it to the supported Qt runnable API and consolidate background task ownership.
- **Regression tests needed:** Import smoke and one task success/failure/lifetime test if retained.
- **Implementation complexity:** S.

## CI evidence

[Main CI run](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/42718526490): all four OS/Python matrix jobs failed. Detailed test summaries were inspected for Ubuntu/Python 3.12 and Windows/Python 3.12; other job failures are not assumed to have identical causes.

[UI acceptance run](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/42718526309): all Windows scale jobs failed, all Ubuntu scale jobs passed. Detailed clipping findings above come from Windows scale 1.5 job 129506208938. [Screenshot artifact](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/42718526309/artifacts/13717959445).
