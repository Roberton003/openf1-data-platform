"""Tests for authentication, rate limiting, and CORS middleware.

Auth is optional — without OPENF1_API_KEY, the API is open (dev mode).
With OPENF1_API_KEY set, all protected endpoints require X-API-Key
or Authorization: Bearer <key>.
"""

import os

from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app

VALID_KEY = "test-api-key-12345"
PROTECTED_PATH = "/api/telemetry?session_key=10014&driver_number=44"


def _make_client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)


# ---------------------------------------------------------------------------
# No API key — auth bypassed (dev mode)
# ---------------------------------------------------------------------------


class TestWithoutApiKey:
    def setup_method(self):
        os.environ.pop("OPENF1_API_KEY", None)

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_bypass_returns_200(self, mock_db):
        client = _make_client(mock_db)
        resp = client.get(PROTECTED_PATH)
        assert resp.status_code == 200

    def test_sql_gateway_bypass(self, mock_db):
        client = _make_client(mock_db)
        resp = client.post("/api/analytics/query", json={"query": "SELECT 1"})
        assert resp.status_code != 401


# ---------------------------------------------------------------------------
# With API key — auth enforced
# ---------------------------------------------------------------------------


class TestWithApiKey:
    def setup_method(self):
        os.environ["OPENF1_API_KEY"] = VALID_KEY

    def teardown_method(self):
        os.environ.pop("OPENF1_API_KEY", None)
        app.dependency_overrides.clear()

    def test_401_missing_api_key(self, mock_db):
        client = _make_client(mock_db)
        resp = client.get(PROTECTED_PATH)
        assert resp.status_code == 401

    def test_401_invalid_api_key(self, mock_db):
        client = _make_client(mock_db)
        headers = {"X-API-Key": "wrong-key"}
        resp = client.get(PROTECTED_PATH, headers=headers)
        assert resp.status_code == 401

    def test_200_valid_api_key_header(self, mock_db):
        client = _make_client(mock_db)
        headers = {"X-API-Key": VALID_KEY}
        resp = client.get(PROTECTED_PATH, headers=headers)
        assert resp.status_code == 200

    def test_200_valid_bearer_token(self, mock_db):
        client = _make_client(mock_db)
        headers = {"Authorization": f"Bearer {VALID_KEY}"}
        resp = client.get(PROTECTED_PATH, headers=headers)
        assert resp.status_code == 200
