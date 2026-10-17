"""
Shared pytest fixtures for Pharma-Khaato core test suite.
Each test gets an isolated temp database via PHARMA_KHAATO_DATA_DIR.
"""

import os
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Isolated database per test: migrations run against a temp dir."""
    data_dir = tmp_path / "pk_data"
    monkeypatch.setenv("PHARMA_KHAATO_DATA_DIR", str(data_dir))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    # PathManager caches the resolved dir — reset it per test.
    from core.path_manager import PathManager
    PathManager._BASE_DATA_DIR = None

    import importlib
    from core import db_engine
    db_engine.reset_thread_connections()
    yield db_engine
    db_engine.reset_thread_connections()
    PathManager._BASE_DATA_DIR = None


@pytest.fixture()
def seeded_shop(fresh_db):
    """Minimal supplier/product/batch/admin ready to transact."""
    from core import auth_service, db_engine
    conn = db_engine.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Supplier (supplier_name, supplier_company_name, Email_address, phone_number) "
        "VALUES ('Sup', 'Co', 's@s.com', '0300')"
    )
    cur.execute(
        "INSERT INTO Products (product_name, company_name, category, barcode, stock_quantity, price) "
        "VALUES ('TestMed', 'Co', 'Cat', 'BC1', 100, 15.0)"
    )
    cur.execute(
        "INSERT INTO Batch (product_id, number_of_product, quantity, expiry_date, manufacture_Date, supplier_id) "
        "VALUES (1, 'B1', 100, '2099-12-31', '2026-01-01', 1)"
    )
    auth_service.register_initial_admin("admin", "secret123", "Test", "Admin")
    conn.commit()
    return db_engine


@pytest.fixture()
def admin_emp_id(seeded_shop):
    cur = seeded_shop.get_conn().cursor()
    cur.execute("SELECT Employee_id FROM Employee WHERE username='admin'")
    return cur.fetchone()[0]


@pytest.fixture()
def cash_shift(seeded_shop, admin_emp_id):
    """An explicitly opened local counter for tests accepting physical cash."""
    from core.cash_session_service import open_session
    ok, session_id = open_session(admin_emp_id, 0)
    assert ok, session_id
    return session_id
