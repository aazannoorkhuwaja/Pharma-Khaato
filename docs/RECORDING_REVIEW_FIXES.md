# Pharmacy recording review follow-up

Baseline: upstream main `55a06334ac02fe0d567852061dea5f05e5180c70`. The linked `/workspace/video-review/REVIEW.md` was not present locally; the owner's fifteen findings are the acceptance list.

| # | Finding | Change / verification |
|---|---|---|
| 1 | Dark-mode form labels | Scroll surfaces and application palette use active theme; inventory headings use semantic styles. Actual light/dark Qt rendering tested. |
| 2 | Clipped stock entry | Removed 430px cap, balanced form/list space, wrap long form rows and allow fields to grow. Horizontal-scroll regression at 1024/1366px. |
| 3 | Contradictory shift footer | Shared Qt state notification on confirmed open/close; asynchronous initial status read. |
| 4 | Hidden checkout total | Total and change moved outside payment scroll next to Complete Sale. |
| 5 | Generated customer reference | Internal selection identity retained; name and result rows hide generated references. |
| 6 | Calendar in 1900 | Blank expiry retains validation; opening the calendar shows the current month. |
| 7 | Orphan expiry labels | Form rows, including labels, toggle together. |
| 8 | Long product form | Optional detail rows collapse while preserving entered values. |
| 9 | Setup/sign-in handoff | Prefill new username only; password remains blank. |
| 10 | No preparation guide | Automatic first-use checklist plus persistent sidebar entry with supplier, medicine, stock and cash actions. |
| 11 | Ambiguous search | Separate missing-medicine / no-saleable-stock explanations, with cashier-safe server method. |
| 12 | Empty supplier accounts | Add First Supplier action opens the real supplier form. |
| 13 | Empty customer credit | Distinct empty, no-search-match and load-failure explanations. |
| 14 | Premature Close Shift | Disabled until count confirmed; changing the amount resets confirmation. |
| 15 | Cash discrepancy / summary | Explicit acknowledgement for every nonzero difference; last close read from stored figures, scoped to staff and counter over LAN. |

Setup and sign-in already worked. Unreceived stock was correctly unavailable. The expected Rs.5,000 and counted Rs.500 were not corrupted; regression verifies the saved difference remains -Rs.4,500.

## Validation

Regression tests live in `tests/test_recording_review.py`, with startup handoff assertions in `test_first_use_flow.py` and LAN permissions in `test_lan_service.py`. Source UI audit and compilation pass. The source installed-runtime check passes owner setup, sign-in, stock, checkout/retry, receipt, TLS certificate and eight screens.

Local full-suite run before the final rendering refinements: **256 passed; 11 LAN setup errors** caused by the execution sandbox denying server socket creation (`PermissionError: Operation not permitted`). These tests remain enabled and must pass on GitHub's Windows/Linux runners. No test was skipped or weakened to hide this restriction.

Native packaged build results, Windows signing and physical printer/scanner acceptance must be recorded separately. No live shop data was read or reset.
