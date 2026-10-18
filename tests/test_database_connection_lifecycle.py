"""Connections must release Windows file locks without discarding active work."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest


def test_shutdown_drains_worker_and_closes_every_connection(seeded_shop):
    db = seeded_shop
    main_connection = db.get_conn().raw_conn
    started, release, closing_started, closed = Event(), Event(), Event(), Event()
    seen = []
    def write():
        with db.get_db(immediate=True) as (conn, cur):
            seen.append(conn.raw_conn)
            cur.execute("UPDATE Products SET product_name='Committed before close' WHERE id=1")
            started.set()
            assert release.wait(5)
    def close():
        closing_started.set()
        db.close_all_connections()
        closed.set()
    def read_again():
        with db.get_db() as (conn, cur):
            cur.execute('SELECT product_name FROM Products WHERE id=1')
            return conn.raw_conn, cur.fetchone()[0]
    with ThreadPoolExecutor(max_workers=1) as worker, ThreadPoolExecutor(max_workers=1) as closer:
        writing = worker.submit(write)
        try:
            assert started.wait(5)
            closing = closer.submit(close)
            assert closing_started.wait(5)
            assert not closed.wait(0.05), 'Shutdown must wait for the transaction.'
        finally:
            release.set()
        writing.result(timeout=5)
        closing.result(timeout=5)
        assert not db._CONNECTIONS
        for conn in (main_connection, seen[0]):
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute('SELECT 1')
        # This is the same worker thread: its cached closed handle must reopen.
        reopened, name = worker.submit(read_again).result(timeout=5)
        assert reopened is not seen[0]
        assert name == 'Committed before close'
        db.close_all_connections()


def test_shutdown_refuses_an_uncommitted_legacy_transaction(seeded_shop):
    db = seeded_shop
    conn = db.get_conn().raw_conn
    conn.execute('BEGIN IMMEDIATE')
    try:
        with pytest.raises(RuntimeError, match='Finish the current operation'):
            db.close_all_connections()
        assert conn.in_transaction
        assert conn.execute('SELECT COUNT(*) FROM Products').fetchone()[0] == 1
    finally:
        conn.rollback()
        db.close_all_connections()


def test_transaction_context_closes_its_cursor(fresh_db):
    with fresh_db.get_db() as (_conn, cursor):
        cursor.execute('SELECT 1 UNION ALL SELECT 2')
        assert cursor.fetchone() == (1,)
    with pytest.raises(sqlite3.ProgrammingError):
        cursor.fetchone()


def test_failed_initialisation_releases_unregistered_connection(fresh_db, monkeypatch):
    opened = []
    connect = fresh_db.sqlite3.connect
    def track(*args, **kwargs):
        conn = connect(*args, **kwargs)
        opened.append(conn)
        return conn
    def fail_migration(*args, **kwargs):
        raise RuntimeError('Injected migration error')
    monkeypatch.setattr(fresh_db.sqlite3, 'connect', track)
    monkeypatch.setattr(fresh_db.MigrationManager, 'apply_migrations', fail_migration)
    with pytest.raises(RuntimeError, match='Injected migration error'):
        fresh_db.get_conn()
    assert opened
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')
        assert conn not in fresh_db._CONNECTIONS
