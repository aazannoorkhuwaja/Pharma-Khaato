# Transaction and retry safety audit

This document records the transaction boundaries used for money- and stock-changing workflows. It is intentionally explicit about which operations are truly idempotent and which require a refresh before a user retries after an uncertain result.

## Checkout / sale

**Boundary:** `core.pos_service.confirm_sale` owns the sale transaction. Product/batch deductions use conditional stock updates and a failure rolls the database transaction back.

**Duplicate protection:** checkout uses the durable `Checkout_Request` lifecycle introduced by migrations 016/017. A request token is tied to the committed `Purchase` in the same database commit, closing the crash window between sale commit and acknowledgement. A repeated request with the same token resolves to the already committed sale rather than creating another purchase.

**Safe retry rule:** the UI may retry the same durable checkout request token. It must not manufacture a new token merely because an acknowledgement was lost.

## Returns / refunds

**Boundary:** `core.return_service.process_return` serializes a return with a write transaction. It derives refundable quantities and prices from the original purchase, subtracts quantities already returned, records the return/refund, and applies any restock or credit-ledger adjustment together.

**Invariant protection:** callers cannot increase a refund by supplying a forged price or return more than the remaining sold quantity. Refund tender is derived from recorded transaction history rather than trusted from the UI.

**Idempotency:** a return is a business action, not currently a token-idempotent request. Two different partial returns can both be valid.

**Safe retry rule:** after an uncertain return result, refresh the purchase/return state before submitting another return. Do not blindly resubmit the same return as a new action.

## Customer-credit collection

**Boundary:** `core.credit_payment_service.record_credit_payment` acquires a SQLite write transaction before reading the remaining balance. The balance check, optional open-cash-shift lookup, ledger update, and `Credit_Payment` history insert are performed together.

**Concurrency protection:** the ledger update also matches the previously read due/paid values. A stale concurrent collection cannot silently over-collect; the caller is told to refresh.

**Idempotency:** credit collection does not currently use a durable request token because repeated partial collections may be legitimate separate payments.

**Safe retry rule:** after an uncertain payment result, refresh the customer ledger/payment history first. Never auto-retry by creating a second payment record without confirming the first result.

## Cash movements and shift close

**Cash movement:** a manual cash entry requires the acting employee to own the open shift and have `cash.own_shift` permission.

**Shift close boundary:** `core.cash_session_service.close_session` verifies the acting employee and shift owner, starts a write transaction, computes expected physical cash from the same database snapshot, and changes the shift to `CLOSED` in that transaction. A sale, collection, refund, or manual movement cannot be inserted between reconciliation and the close update.

**Safe retry rule:** refresh shift status after an uncertain close result. A second close of an already closed shift is rejected.

## Permission boundaries considered during this audit

Money-changing service entry points are expected to validate the acting employee rather than rely only on hidden UI buttons. In particular:

- sales require `pos.sell`;
- returns require `returns.process`;
- credit collection requires `credit.collect`;
- cash shift/movement operations require `cash.own_shift` and ownership checks.

Administrative/staff/settings mutations are audited separately in the role/permission hardening work.

## Testing expectations

Regression coverage should exercise at least:

- duplicate/durable checkout behaviour;
- return quantity/tender invariants;
- simultaneous credit-payment attempts against the same balance;
- cross-staff cash-shift close rejection;
- complete rollback on migration/restore failure paths.

A green CI run is necessary but not a replacement for the manual pharmacy workflow and hardware acceptance tests.
