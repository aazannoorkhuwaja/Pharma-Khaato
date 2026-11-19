import os
import glob
import hashlib
import re
import sqlite3
from datetime import datetime

from core.logger import get_logger
from core.path_manager import PathManager

logger = get_logger("PharmaKhaatoMigration")


class MigrationManager:
    """Transactional, version-ordered SQLite migration manager."""

    _MIGRATION_NAME = re.compile(r"^(\d+)_.*\.sql$")

    # A previously distributed index migration was renumbered from 014 to 015.
    # Some shops recorded both names. Only accept the redundant legacy entry
    # when its canonical replacement is also recorded; schema validation still
    # verifies every index definition. Never treat arbitrary unknowns as aliases.
    _HISTORICAL_ALIASES = {"014_ui_performance_indexes.sql": "015_ui_performance_indexes.sql"}

    @classmethod
    def canonical_history(cls, applied, known):
        history = set(applied)
        for legacy, canonical in cls._HISTORICAL_ALIASES.items():
            if legacy in history and canonical in history and canonical in known:
                history.remove(legacy)
        if history - set(known):
            raise ValueError("This backup requires a different application version.")
        return history

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
            version = str(int(match.group(1)))
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

        from core.financial_storage import register
        register(raw_conn)
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
        recorded = applied
        try:
            applied = cls.canonical_history(recorded, {os.path.basename(path) for path in mig_files})
        except ValueError as exc:
            raise RuntimeError("This database requires a newer or different application version.") from exc
        digests = {os.path.basename(path): hashlib.sha256(open(path, 'rb').read()).hexdigest() for path in mig_files}
        columns = {row[1] for row in cur.execute("PRAGMA table_info(schema_migrations)")}
        existing_hashes = dict(cur.execute("SELECT version,checksum FROM schema_migrations")) if "checksum" in columns else {}
        for version, checksum in existing_hashes.items():
            if version in recorded - applied:
                if checksum:
                    raise RuntimeError(f"Unrecognized historical migration checksum: {version}.")
                continue
            if checksum and checksum != digests[version]:
                raise RuntimeError(f"Migration checksum differs: {version}. Restore matching application files.")
        if applied:
            from core.schema_validation import validate_declared_schema
            validate_declared_schema(raw_conn, recorded)
        if "checksum" not in columns:
            cur.execute("ALTER TABLE schema_migrations ADD COLUMN checksum TEXT")
        for version in applied:
            if not existing_hashes.get(version):
                cur.execute("UPDATE schema_migrations SET checksum=? WHERE version=?", (digests[version], version))
        raw_conn.commit()
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
                    "INSERT INTO schema_migrations (version, applied_at, checksum) VALUES (?, ?, ?)",
                    (filename, datetime.now().isoformat(), digests[filename]),
                )
                raw_conn.commit()
                logger.info("Successfully applied migration: %s", filename)
            except Exception as exc:
                raw_conn.rollback()
                logger.error("Failed applying migration %s: %s", filename, exc)
                raise RuntimeError(f"Database migration failure on {filename}: {exc}") from exc
