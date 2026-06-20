"""Tests for rate limiting middleware."""

import pytest
from fastapi.testclient import TestClient

from src.web import auth
from src.web.database import get_db
from src.web.main import app


@pytest.fixture
def client(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    auth._rate_store.clear()
    with TestClient(app) as c:
        yield c
    auth._rate_store.clear()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(overrides_before)


def test_rate_limit_allowed(client):
    """Requests under default limit return 200."""
    for _ in range(5):
        resp = client.post("/api/analytics/query", json={"query": "SELECT 1"})
        assert resp.status_code == 200


def test_rate_limit_exceeded(client, monkeypatch):
    """Requests over limit return 429 with error detail."""
    monkeypatch.setattr(auth, "_get_rate_limit", lambda: 2)
    auth._rate_store.clear()
    client.post("/api/analytics/query", json={"query": "SELECT 1"})
    client.post("/api/analytics/query", json={"query": "SELECT 1"})
    resp = client.post("/api/analytics/query", json={"query": "SELECT 1"})
    assert resp.status_code == 429
    data = resp.json()
    assert "Limite de taxa excedido" in data["detail"]


def test_rate_limit_bypass_get(client, monkeypatch):
    """GET requests bypass rate limiting."""
    monkeypatch.setattr(auth, "_get_rate_limit", lambda: 1)
    auth._rate_store.clear()
    for _ in range(5):
        resp = client.get("/api/health")
        assert resp.status_code == 200


def test_rate_limit_bypass_non_query_post(client, monkeypatch):
    """POST to non-/api/analytics/query endpoints bypasses rate limiting."""
    monkeypatch.setattr(auth, "_get_rate_limit", lambda: 1)
    auth._rate_store.clear()
    for _ in range(5):
        resp = client.post(
            "/api/analytics/chat",
            json={"session_key": 10014, "question": "test"},
        )
        assert resp.status_code == 200
