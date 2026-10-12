-- Migration 009: Persistent login lockout tracking
-- Replaces in-memory-only brute-force lockout so it survives application restarts.
CREATE TABLE IF NOT EXISTS Login_Lockout (
    username TEXT PRIMARY KEY,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0.0
);
