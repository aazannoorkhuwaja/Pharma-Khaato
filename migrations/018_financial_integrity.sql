-- Explicit operation identity and immutable sale facts. Do not infer a token
-- from whichever employee request happened to be prepared most recently.
DROP TRIGGER IF EXISTS purchase_checkout_request_ai;
ALTER TABLE Checkout_Request ADD COLUMN request_fingerprint TEXT;
ALTER TABLE Purchase ADD COLUMN held_sale_id INTEGER REFERENCES Hold_Sales(id);
ALTER TABLE Purchase ADD COLUMN cash_received REAL;
ALTER TABLE Purchase ADD COLUMN change_due REAL NOT NULL DEFAULT 0;
ALTER TABLE Purchase ADD COLUMN tax_rate REAL;
ALTER TABLE Purchase ADD COLUMN total_tax REAL;
ALTER TABLE Purchase ADD COLUMN terminal_id TEXT;
ALTER TABLE Hold_Sales ADD COLUMN purchase_id INTEGER REFERENCES Purchase(id);
ALTER TABLE Hold_Sales ADD COLUMN draft_json TEXT;
ALTER TABLE Sales_details ADD COLUMN unit_code TEXT NOT NULL DEFAULT 'base';
ALTER TABLE Sales_details ADD COLUMN unit_multiplier INTEGER NOT NULL DEFAULT 1;
ALTER TABLE Sales_details ADD COLUMN display_quantity REAL;
ALTER TABLE Cash_Register_Session ADD COLUMN terminal_id TEXT NOT NULL DEFAULT 'local';
CREATE INDEX IF NOT EXISTS idx_cash_terminal_status ON Cash_Register_Session(terminal_id,status);
CREATE TRIGGER IF NOT EXISTS cash_one_open_terminal BEFORE INSERT ON Cash_Register_Session
WHEN NEW.status='OPEN' AND EXISTS(SELECT 1 FROM Cash_Register_Session
 WHERE terminal_id=NEW.terminal_id AND status='OPEN')
BEGIN SELECT RAISE(ABORT,'This counter already has an open cash shift.'); END;
CREATE TABLE IF NOT EXISTS Cash_Operation(
 operation_id TEXT PRIMARY KEY,employee_id INTEGER NOT NULL,request_fingerprint TEXT NOT NULL,
 result_json TEXT NOT NULL,created_at TEXT NOT NULL
);

-- Preserve the prior effective rate on upgrade and retain the original value
-- for review. Legacy values (0,1] have ambiguous units, so flag them explicitly.
INSERT OR IGNORE INTO Pharmacy_Settings(setting_key,setting_value)
SELECT 'legacy_default_tax_rate',setting_value FROM Pharmacy_Settings
WHERE setting_key='default_tax_rate';
INSERT OR IGNORE INTO Pharmacy_Settings(setting_key,setting_value)
SELECT 'tax_rate_review_required',CASE
  WHEN CAST(setting_value AS REAL)>0 AND CAST(setting_value AS REAL)<=1 THEN '1'
  ELSE '0' END FROM Pharmacy_Settings WHERE setting_key='default_tax_rate';
UPDATE Pharmacy_Settings SET setting_value=CAST(CAST(setting_value AS REAL)*100 AS TEXT)
WHERE setting_key='default_tax_rate' AND CAST(setting_value AS REAL)>0
  AND CAST(setting_value AS REAL)<=1
  AND NOT EXISTS(SELECT 1 FROM Pharmacy_Settings WHERE setting_key='default_tax_rate_format');
INSERT OR IGNORE INTO Pharmacy_Settings(setting_key,setting_value)
VALUES ('default_tax_rate_format','percent_v1');
