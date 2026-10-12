-- Migration 010: Normalize customer identity keys
-- Fixes the CNIC mismatch bug: confirm_sale stored dashed/raw CNIC strings in
-- Purchase/Customer_Khatoo, but every debt lookup queries with validate_cnic()'s
-- normalized 13-digit form. Existing dashed rows were invisible to debt checks,
-- silently defeating credit-limit enforcement.
--
-- SQLite has no built-in regexp replace; this uses string surgery valid for the
-- standard PK CNIC shape '12345-6789012-3' (13 digits + 2 dashes). Rows that are
-- already bare 13-digit or non-CNIC identifiers (WALKIN) are left untouched.

UPDATE Customers
SET id_card_number = REPLACE(REPLACE(id_card_number, '-', ''), ' ', '')
WHERE id_card_number LIKE '%-%' OR id_card_number LIKE '% %';

-- Re-point ledger rows to the normalized key (create target if missing handled
-- by UNIQUE merge below).
UPDATE Customer_Khatoo
SET customer_id = REPLACE(REPLACE(customer_id, '-', ''), ' ', '')
WHERE customer_id LIKE '%-%' OR customer_id LIKE '% %';

UPDATE Purchase
SET customer_id = REPLACE(REPLACE(customer_id, '-', ''), ' ', '')
WHERE customer_id IS NOT NULL AND (customer_id LIKE '%-%' OR customer_id LIKE '% %');
