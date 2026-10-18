import os
import sys
import time
import logging
import sqlite3
import platform
import threading
from decimal import Decimal
from contextlib import contextmanager

from core.logger import get_logger
from core.path_manager import PathManager
from core.migration_manager import MigrationManager
from config import ApplicationSettings

logger = get_logger("PharmaKhaatoDB")

# Register Decimal adapters to eliminate floating-point representation drift
sqlite3.register_adapter(Decimal, lambda d: str(d))
sqlite3.register_converter("DECIMAL", lambda s: Decimal(s.decode("utf-8")))

_TRANSLATION_CACHE = {}
_THREAD_LOCAL = threading.local()
_MIGRATED_PATHS = set()
_MIGRATION_LOCK = threading.Lock()
_SQLITE_BUSY_TIMEOUT_MS = 3000
_DB_GATE = threading.RLock()
_CONNECTIONS = set()
_RESTART_PATHS = set()


def bounded_setting(name, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(os.environ.get(name, default))))
    except (TypeError, ValueError):
        return default


@contextmanager
def database_guard():
    """Exclude maintenance while an operation is using the local store."""
    with _DB_GATE:
        yield


def close_all_connections():
    """Drain managed work, then close connections owned by every worker thread.

    Resetting just the caller's thread-local cache leaves Qt worker connections
    alive and keeps the SQLite files locked on Windows.
    """
    with _DB_GATE:
        for conn in list(_CONNECTIONS):
            try:
                active = conn.in_transaction
            except sqlite3.ProgrammingError:
                # A caller may already have closed the underlying connection.
                _CONNECTIONS.discard(conn)
                continue
            if active:
                raise RuntimeError("Finish the current operation before closing the database.")
        for conn in list(_CONNECTIONS):
            conn.close()
            _CONNECTIONS.discard(conn)
        _THREAD_LOCAL.sqlite_conn = None
        _THREAD_LOCAL.sqlite_path = None


@contextmanager
def database_maintenance():
    """Drain managed transactions and close worker connections before replacement."""
    with _DB_GATE:
        close_all_connections()
        _MIGRATED_PATHS.discard(PathManager.get_db_path())
        yield


class UnifiedCursor:
    """Cursor wrapper that translates SQL syntax where necessary."""
    def __init__(self, cursor, is_sqlite=False):
        self._cursor = cursor
        self.is_sqlite = is_sqlite

    def execute(self, sql, params=None):
        with _DB_GATE:
            return self._execute(sql, params)

    def _execute(self, sql, params=None):
        if self.is_sqlite:
            sql = self._translate_sql(sql)
            if params is None:
                return self._cursor.execute(sql)
            return self._cursor.execute(sql, params)
        else:
            if params is None:
                return self._cursor.execute(sql)
            return self._cursor.execute(sql, params)

    def close(self):
        self._cursor.close()

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return getattr(self._cursor, "rowcount", -1)

    def _translate_sql(self, sql):
        if sql in _TRANSLATION_CACHE:
            return _TRANSLATION_CACHE[sql]

        translated = sql.replace("%s", "?")
        translated = translated.replace("CURDATE()", "DATE('now')")
        translated = translated.replace("DATE_ADD(DATE('now'), INTERVAL ? DAY)", "DATE('now', '+' || ? || ' days')")
        translated = translated.replace("DATE_ADD(CURDATE(), INTERVAL ? DAY)", "DATE('now', '+' || ? || ' days')")
        translated = translated.replace("FOR UPDATE", "")

        _TRANSLATION_CACHE[sql] = translated
        return translated


class UnifiedConnection:
    """SQLite connection wrapper with resource management."""
    def __init__(self, raw_conn, is_sqlite=False, engine_type="SQLite", is_persistent=True):
        self.raw_conn = raw_conn
        self.is_sqlite = is_sqlite
        self.engine_type = engine_type
        self.is_persistent = is_persistent

    def cursor(self):
        return UnifiedCursor(self.raw_conn.cursor(), is_sqlite=self.is_sqlite)

    def commit(self):
        with _DB_GATE:
            self.raw_conn.commit()

    def rollback(self):
        with _DB_GATE:
            self.raw_conn.rollback()

    def close(self, force=False):
        """Clean connection close API. Safe no-op for persistent thread-local connections unless force=True."""
        if self.is_persistent and not force:
            logger.debug("Retaining persistent database connection for thread reuse.")
            return
        try:
            if self.is_sqlite and hasattr(_THREAD_LOCAL, "sqlite_conn"):
                _THREAD_LOCAL.sqlite_conn = None
                _THREAD_LOCAL.sqlite_path = None
            self.raw_conn.close()
            _CONNECTIONS.discard(self.raw_conn)
            logger.debug("Database connection closed cleanly.")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")


def _get_sqlite_connection():
    """Initialize and return a long-lived thread-local SQLite connection."""
    db_path = PathManager.get_db_path()
    from core.backup_service import recover_interrupted_restore
    recover_interrupted_restore()

    if hasattr(_THREAD_LOCAL, "sqlite_conn") and _THREAD_LOCAL.sqlite_conn is not None:
        if getattr(_THREAD_LOCAL, "sqlite_path", None) == db_path:
            try:
                _THREAD_LOCAL.sqlite_conn.execute("SELECT 1")
                return UnifiedConnection(_THREAD_LOCAL.sqlite_conn, is_sqlite=True, engine_type="SQLite")
            except (sqlite3.Error, OSError) as e:
                logger.warning(f"Handled connection liveness notice: {e}")
                _CONNECTIONS.discard(_THREAD_LOCAL.sqlite_conn)
                _THREAD_LOCAL.sqlite_conn = None
                _THREAD_LOCAL.sqlite_path = None

    first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        timeout=_SQLITE_BUSY_TIMEOUT_MS / 1000.0,
    )

    try:
        # High-performance desktop settings. WAL keeps reads concurrent with normal
        # writes; a short busy timeout avoids turning lock contention into a
        # 15-second apparent application freeze.
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = FULL;")
        cache_kib = bounded_setting("PHARMA_KHAATO_CACHE_KIB", 8192, 1024, 32768)
        conn.execute(f"PRAGMA cache_size = -{cache_kib};")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(f"PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS};")

        if first_time:
            logger.info(f"Creating fresh SQLite embedded database at: {db_path}")
            schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema_sqlite.sql")
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
                conn.commit()
                logger.info("SQLite schema initialized successfully.")

        # Apply migrations once per database path process-wide.
        if db_path not in _MIGRATED_PATHS:
            with _MIGRATION_LOCK:
                if db_path not in _MIGRATED_PATHS:
                    MigrationManager.apply_migrations(conn, is_sqlite=True, new_database=first_time)
                    _MIGRATED_PATHS.add(db_path)

    except BaseException:
        # Failed setup is not registered yet, so global shutdown cannot find it.
        conn.close()
        raise

    _THREAD_LOCAL.sqlite_conn = conn
    _THREAD_LOCAL.sqlite_path = db_path
    _CONNECTIONS.add(conn)

    return UnifiedConnection(conn, is_sqlite=True, engine_type="SQLite")


def get_conn():
    """Main database connection factory for the local SQLite database."""
    with _DB_GATE:
        if PathManager.get_db_path() in _RESTART_PATHS:
            raise RuntimeError("Recovery completed. Restart Pharma Khaato before continuing work.")
        return _get_sqlite_connection()


def reset_thread_connections():
    """Reset the current thread's persistent SQLite connection."""
    with _DB_GATE:
        if hasattr(_THREAD_LOCAL, "sqlite_conn") and _THREAD_LOCAL.sqlite_conn is not None:
            try:
                _THREAD_LOCAL.sqlite_conn.close()
                _CONNECTIONS.discard(_THREAD_LOCAL.sqlite_conn)
            except (sqlite3.Error, OSError) as e:
                logger.warning(f"Handled non-critical error closing sqlite connection: {e}")
            _THREAD_LOCAL.sqlite_conn = None
            _THREAD_LOCAL.sqlite_path = None


@contextmanager
def get_db(immediate=False):
    """Own one transaction; nested helpers never commit their caller's writes.

    ``immediate=True`` acquires the write reservation before reading balances
    or stock. A savepoint protects callers that already own a transaction.
    """
    with _DB_GATE:
        conn = get_conn()
        cur = conn.cursor()
        try:
            nested = conn.raw_conn.in_transaction
            savepoint = f"pk_nested_{time.monotonic_ns()}"
            if nested:
                cur.execute(f"SAVEPOINT {savepoint}")
            else:
                cur.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield conn, cur
                if nested:
                    cur.execute(f"RELEASE SAVEPOINT {savepoint}")
                else:
                    conn.commit()
            except Exception:
                if nested:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    cur.execute(f"RELEASE SAVEPOINT {savepoint}")
                else:
                    conn.rollback()
                raise
        finally:
            cur.close()
