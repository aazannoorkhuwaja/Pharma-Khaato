import os
import sys
import tempfile
import shutil
import pytest

# Enforce offscreen Qt rendering for headless test execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Isolate database for tests using a temporary directory
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="pharma_test_db_")
os.environ["PHARMA_KHAATO_DATA_DIR"] = _TEST_TEMP_DIR

from core.path_manager import PathManager
PathManager._BASE_DATA_DIR = os.path.abspath(_TEST_TEMP_DIR)
PathManager.ensure_directories()

# Initialize DB connection and seed default test data
from core.db_engine import get_conn
conn = get_conn()
conn.close()

from scripts.seed_db import seed_database
seed_database()

def pytest_unconfigure(config):
    try:
        shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass
