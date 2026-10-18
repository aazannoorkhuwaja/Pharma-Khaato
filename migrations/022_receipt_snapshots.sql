-- Receipt content commits with its sale; printer delivery is independent.
CREATE TABLE IF NOT EXISTS Receipt_Snapshot (
    purchase_id INTEGER PRIMARY KEY,
    receipt_text TEXT NOT NULL,
    template TEXT NOT NULL,
    created_at TEXT NOT NULL,
    print_status TEXT NOT NULL DEFAULT 'SAVED',
    print_attempts INTEGER NOT NULL DEFAULT 0,
    last_printed_at TEXT,
    FOREIGN KEY(purchase_id) REFERENCES Purchase(id) ON DELETE RESTRICT
);

CREATE TRIGGER IF NOT EXISTS receipt_snapshot_immutable
BEFORE UPDATE OF receipt_text, template, created_at, purchase_id ON Receipt_Snapshot
BEGIN
    SELECT RAISE(ABORT, 'Saved receipt content cannot be changed');
END;
