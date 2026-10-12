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

class UnifiedCursor:
    """Cursor wrapper that translates SQL syntax where necessary."""
    def __init__(self, cursor, is_sqlite=False):
        self._cursor = cursor
        self.is_sqlite = is_sqlite

    def execute(self, sql, params=None):
        if self.is_sqlite:
            sql = self._translate_sql(sql)
            if params is None:
                return self._cursor.execute(sql)
            return self._cursor.execute(sql, params)
        else:
            if params is None:
                return self._cursor.execute(sql)
            return self._cursor.execute(sql, params)

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
        self.raw_conn.commit()

    def rollback(self):
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
            logger.debug("Database connection closed cleanly.")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")


def _get_sqlite_connection():
    """Initializes and returns a long-lived thread-local SQLite database connection with performance PRAGMAs."""
    db_path = PathManager.get_db_path()

    # Reuse thread-local connection if active for the same db_path
    if hasattr(_THREAD_LOCAL, "sqlite_conn") and _THREAD_LOCAL.sqlite_conn is not None:
        if getattr(_THREAD_LOCAL, "sqlite_path", None) == db_path:
            try:
                # Test connection Liveness
                _THREAD_LOCAL.sqlite_conn.execute("SELECT 1")
                return UnifiedConnection(_THREAD_LOCAL.sqlite_conn, is_sqlite=True, engine_type="SQLite")
            except (sqlite3.Error, OSError) as e:
                logger.warning(f"Handled connection liveness notice: {e}")
                _THREAD_LOCAL.sqlite_conn = None
                _THREAD_LOCAL.sqlite_path = None

    first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # High Performance PRAGMA tuning
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB memory cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 15000;")
    
    if first_time:
        logger.info(f"Creating fresh SQLite embedded database at: {db_path}")
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema_sqlite.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
            logger.info("SQLite schema initialized successfully.")
    
    # Apply migrations ONCE per db_path process-wide to avoid overhead on every query
    if db_path not in _MIGRATED_PATHS:
        with _MIGRATION_LOCK:
            if db_path not in _MIGRATED_PATHS:
                MigrationManager.apply_migrations(conn, is_sqlite=True)
                _MIGRATED_PATHS.add(db_path)

    _THREAD_LOCAL.sqlite_conn = conn
    _THREAD_LOCAL.sqlite_path = db_path

    return UnifiedConnection(conn, is_sqlite=True, engine_type="SQLite")


def get_conn():
    """
    Main database connection factory.
    Operates exclusively on local SQLite database in WAL mode.
    """
    return _get_sqlite_connection()


def reset_thread_connections():
    """Resets and closes all thread-local persistent database connections for safe backup/restore operations."""
    if hasattr(_THREAD_LOCAL, "sqlite_conn") and _THREAD_LOCAL.sqlite_conn is not None:
        try:
            _THREAD_LOCAL.sqlite_conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.warning(f"Handled non-critical error closing sqlite connection: {e}")
        _THREAD_LOCAL.sqlite_conn = None
        _THREAD_LOCAL.sqlite_path = None


@contextmanager
def get_db():
    """
    Context manager for database access. Preferred entry point for all service functions.

    Usage:
        with get_db() as (conn, cur):
            cur.execute(...)
            return cur.fetchall()

    Behaviour:
        - Acquires a long-lived thread-safe connection via get_conn().
        - Yields (UnifiedConnection, UnifiedCursor) to the caller.
        - Calls conn.commit() on clean exit.
        - Calls conn.rollback() if an exception is raised, then re-raises.
        - Reuses long-lived thread connections across operations.
    """
    conn = get_conn()
    if not conn:
        raise RuntimeError("Database connection unavailable.")
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
