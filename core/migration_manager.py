import os
import glob
import re
import sqlite3
from datetime import datetime

from core.logger import get_logger
from core.path_manager import PathManager

logger = get_logger("PharmaKhaatoMigration")


class MigrationManager:
    """Transactional, version-ordered SQLite migration manager."""

    _MIGRATION_NAME = re.compile(r"^(\d+)_.*\.sql$")

    @classmethod
    def _migration_catalog(cls, mig_dir: str) -> list[str]:
        """Return an ordered catalog and reject ambiguous version numbers."""
        files = sorted(glob.glob(os.path.join(mig_dir, "*.sql")))
        seen_versions: dict[str, str] = {}
        for filepath in files:
            filename = os.path.basename(filepath)
            match = cls._MIGRATION_NAME.match(filename)
            if not match:
                raise RuntimeError(
                    f"Invalid migration filename '{filename}'. Use NNN_description.sql."
                )
            version = match.group(1)
            prior = seen_versions.get(version)
            if prior:
                raise RuntimeError(
                    f"Duplicate migration version {version}: '{prior}' and '{filename}'."
                )
            seen_versions[version] = filename
        return files

    @classmethod
    def _create_pre_migration_backup(cls, raw_conn, next_filename: str) -> str | None:
        """Create a verified SQLite copy before upgrading an existing database."""
        try:
            backup_dir = PathManager.get_backups_dir()
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = os.path.splitext(next_filename)[0]
            path = os.path.join(backup_dir, f"pre_migration_{stamp}_{safe_name}.sqlite")
            target = sqlite3.connect(path)
            try:
                raw_conn.backup(target)
                row = target.execute("PRAGMA quick_check").fetchone()
                if not row or str(row[0]).lower() != "ok":
                    raise RuntimeError(f"backup integrity check returned {row!r}")
            finally:
                target.close()
            logger.info("Created pre-migration safety backup: %s", path)
            return path
        except Exception as exc:
            # An upgrade must not proceed if its recovery point cannot be made.
            raise RuntimeError(f"Could not create pre-migration safety backup: {exc}") from exc

    @staticmethod
    def _split_statements(exec_sql: str) -> list[str]:
        """Split SQL using SQLite's parser-aware completeness check.

        A line-oriented BEGIN/END detector is unsafe because ordinary values such as
        'PENDING' contain the substring 'END', which can accidentally split a trigger
        body at its first internal semicolon. ``sqlite3.complete_statement`` tracks
        quoted strings and CREATE TRIGGER BEGIN/END blocks correctly.
        """
        statements: list[str] = []
        buffer: list[str] = []

        for line in exec_sql.splitlines(keepends=True):
            buffer.append(line)
            candidate = "".join(buffer).strip()
            if candidate and sqlite3.complete_statement(candidate):
                statements.append(candidate)
                buffer = []

        remainder = "".join(buffer).strip()
        if remainder:
            raise RuntimeError("Migration SQL ended with an incomplete statement.")

        return statements

    @classmethod
    def apply_migrations(cls, raw_conn, is_sqlite=True, new_database=False):
        """Apply pending migrations transactionally in unambiguous version order."""
        if not is_sqlite:
            raise RuntimeError("Pharma-Khaato migrations currently support SQLite only.")

        cur = raw_conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            """
        )
        raw_conn.commit()

        cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mig_dir = os.path.join(base_dir, "migrations")
        if not os.path.exists(mig_dir):
            return

        mig_files = cls._migration_catalog(mig_dir)
        pending = [path for path in mig_files if os.path.basename(path) not in applied]
        if not pending:
            return

        # Fresh databases are already initialized by schema_sqlite.sql. Existing
        # installations get a recovery point before the first pending upgrade.
        if not new_database:
            cls._create_pre_migration_backup(raw_conn, os.path.basename(pending[0]))

        for filepath in pending:
            filename = os.path.basename(filepath)
            logger.info("Applying database migration script: %s", filename)
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    statements = cls._split_statements(handle.read())

                # Explicit transaction prevents half-applied schema upgrades.
                raw_conn.execute("BEGIN IMMEDIATE")
                for stmt in statements:
                    try:
                        cur.execute(stmt)
                    except sqlite3.Error as stmt_err:
                        err_str = str(stmt_err).lower()
                        if "duplicate column" in err_str or "already exists" in err_str:
                            # Older installations may already contain additive
                            # schema objects created before migration tracking.
                            logger.debug(
                                "Ignored idempotent migration notice in %s: %s",
                                filename,
                                stmt_err,
                            )
                        else:
                            raise

                cur.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (filename, datetime.now().isoformat()),
                )
                raw_conn.commit()
                logger.info("Successfully applied migration: %s", filename)
            except Exception as exc:
                raw_conn.rollback()
                logger.error("Failed applying migration %s: %s", filename, exc)
                raise RuntimeError(f"Database migration failure on {filename}: {exc}") from exc
