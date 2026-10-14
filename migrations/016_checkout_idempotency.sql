-- Durable checkout idempotency for crash/retry safety.
-- A checkout token identifies one cashier submission across retries/restarts.

ALTER TABLE Purchase ADD COLUMN checkout_token TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_purchase_checkout_token
    ON Purchase(checkout_token)
    WHERE checkout_token IS NOT NULL;
