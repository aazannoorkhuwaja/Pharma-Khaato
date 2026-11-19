-- Offboarding revokes authorization without deleting financial/audit history.
ALTER TABLE Employee ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1));
