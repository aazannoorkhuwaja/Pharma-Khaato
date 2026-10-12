import os
import glob
import sqlite3
from datetime import datetime
from core.logger import get_logger

logger = get_logger("PharmaKhaatoMigration")


class MigrationManager:
    """
    Authoritative Migration Manager for Pharma-Khaato.
    Tracks applied migrations in `schema_migrations` table and applies pending
    `.sql` files in version order. SQLite-only engine (MySQL support removed).
    """

    @classmethod
    def apply_migrations(cls, raw_conn, is_sqlite=True):
        """
        Applies all pending migrations in migrations/ directory in sorted order.
        """
        cur = raw_conn.cursor()

        # 1. Ensure tracking table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
        """)
        raw_conn.commit()

        # 2. Get list of already applied migrations
        cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

        # 3. Find all migration files in project/migrations/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mig_dir = os.path.join(base_dir, "migrations")
        if not os.path.exists(mig_dir):
            return

        mig_files = sorted(glob.glob(os.path.join(mig_dir, "*.sql")))

        for filepath in mig_files:
            filename = os.path.basename(filepath)
            if filename in applied:
                continue

            logger.info(f"Applying database migration script: {filename}")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    exec_sql = f.read()

                # Execute statements respecting multi-line trigger blocks
                statements = []
                current_stmt = []
                in_begin = False
                for line in exec_sql.splitlines():
                    clean_line = line.strip()
                    if not clean_line or clean_line.startswith("--"):
                        continue
                    current_stmt.append(line)
                    if "BEGIN" in clean_line.upper():
                        in_begin = True
                    if "END" in clean_line.upper():
                        in_begin = False
                    if clean_line.endswith(";") and not in_begin:
                        statements.append("\n".join(current_stmt))
                        current_stmt = []
                if current_stmt:
                    stmt_str = "\n".join(current_stmt).strip()
                    if stmt_str:
                        statements.append(stmt_str)

                for stmt in statements:
                    try:
                        cur.execute(stmt)
                    except sqlite3.Error as stmt_err:
                        err_str = str(stmt_err).lower()
                        if "duplicate column" in err_str or "already exists" in err_str:
                            logger.debug(f"Ignored non-fatal migration notice in {filename}: {stmt_err}")
                        else:
                            raise stmt_err

                cur.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (filename, datetime.now().isoformat())
                )
                raw_conn.commit()
                logger.info(f"Successfully applied migration: {filename}")
            except Exception as e:
                raw_conn.rollback()
                logger.error(f"Failed applying migration {filename}: {e}")
                raise RuntimeError(f"Database migration failure on {filename}: {e}")
