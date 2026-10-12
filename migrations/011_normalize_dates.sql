-- Migration 011: Normalize expiry dates to ISO YYYY-MM-DD
-- FEFO ordering and the expiry guard compare expiry_date as TEXT against
-- today's padded 'YYYY-MM-DD'. Non-padded values like '2027-1-5' sort
-- incorrectly ('2027-1-5' < '2027-01-01') and can make expired or
-- soon-to-expire stock appear valid.
--
-- SQLite-side normalization of arbitrary date text is fragile, so this
-- migration only fixes the common single-digit month/day case; the app also
-- guards at write time (inventory_service) going forward.

UPDATE Batch
SET expiry_date =
    substr(expiry_date, 1, 5)
    || printf('%02d', CAST(substr(substr(expiry_date, 6), 1, instr(substr(expiry_date, 6), '-') - 1) AS INTEGER))
    || '-'
    || printf('%02d', CAST(replace(substr(substr(expiry_date, 6), instr(substr(expiry_date, 6), '-') + 1), '-', '') AS INTEGER))
WHERE length(expiry_date) <> 10
  AND expiry_date LIKE '____-%'
  AND expiry_date NOT GLOB '*[^0-9-]*';
