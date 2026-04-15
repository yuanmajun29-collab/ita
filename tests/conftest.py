from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ita.api.main import app
from ita.core.database import Database
from ita.core import database as db_module


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path):
    """Use an isolated sqlite DB for each test."""
    db_path = tmp_path / "ita_test.db"
    db_module._db_instance = Database(str(db_path))
    yield
    db_module._db_instance = None


@pytest.fixture
def client():
    return TestClient(app)
