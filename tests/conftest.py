"""Isolated temporary SQLite database and FastAPI client fixtures."""
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    from backend import db
    from backend.main import app
    db.close_connections()
    monkeypatch.setenv("WDMMG_DB", str(tmp_path / "test.db"))
    db.init_db()
    with TestClient(app) as test_client:
        yield test_client
    db.close_connections()

