import os
import glob
import re
import sqlite3

from core.business_time import business_now
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
            stamp = business_now().strftime("%Y%m%d_%H%M%S")
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
    def _is_tolerated_additive_error(message: str) -> bool:
        """True when a statement only re-declares an object that already exists.

        ``schema_sqlite.sql`` is a snapshot of the current schema and the
        catalog is replayed on top of it for version tracking, so an additive
        statement colliding with the base file is expected on a new install as
        well as on an upgrade. Anything that is not a duplicate column or an
        already-existing object is a real failure and stops the migration.
        """
        lowered = message.lower()
        return "duplicate column" in lowered or "already exists" in lowered

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
        """Apply pending migrations transactionally in unambiguous version order.

        Returns the filenames applied in this call, so startup logging and the
        schema-parity test can assert the fresh and upgrade paths agree.
        """
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
            return []

        # A fresh database is initialized from schema_sqlite.sql, which the
        # migration catalog builds on. Only a real upgrade needs a recovery
        # point before its first pending change.
        if not new_database:
            cls._create_pre_migration_backup(raw_conn, os.path.basename(pending[0]))

        tolerated_statements = 0
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
                        if not cls._is_tolerated_additive_error(str(stmt_err)):
                            raise
                        tolerated_statements += 1
                        # Deliberately visible. This used to be hidden at debug
                        # level, which meant a genuinely broken migration looked
                        # exactly like a healthy replay.
                        logger.warning(
                            "Migration %s re-declared an existing object (%s). "
                            "Expected while replaying the catalog over the shipped "
                            "base schema; confirm it is a no-op on an older shop.",
                            filename,
                            stmt_err,
                        )

                cur.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (filename, business_now().isoformat()),
                )
                raw_conn.commit()
                logger.info("Successfully applied migration: %s", filename)
            except Exception as exc:
                raw_conn.rollback()
                logger.error("Failed applying migration %s: %s", filename, exc)
                raise RuntimeError(f"Database migration failure on {filename}: {exc}") from exc

        if tolerated_statements:
            logger.info(
                "Replayed %d migration statement(s) already present in the base schema.",
                tolerated_statements,
            )
        return [os.path.basename(path) for path in pending]
