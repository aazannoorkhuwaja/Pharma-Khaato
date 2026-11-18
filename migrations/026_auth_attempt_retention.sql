-- Retain bounded-age unsuccessful login attempts, including non-locking rows.
ALTER TABLE Login_Lockout ADD COLUMN last_attempt REAL NOT NULL DEFAULT 0;
UPDATE Login_Lockout SET last_attempt = CAST(strftime('%s','now') AS REAL);
CREATE INDEX IF NOT EXISTS idx_login_attempt_age ON Login_Lockout(last_attempt);
