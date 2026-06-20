"""Tests for web/routers/race_intelligence.py — endpoint tests."""

from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app

client = TestClient(app)


def test_session_summary_empty_db(monkeypatch, mock_db):
    monkeypatch.setattr("src.web.routers.race_intelligence.get_db", lambda: mock_db)
    response = client.get("/api/race_intelligence/session_summary?session_key=99999")
    assert response.status_code == 200
    body = response.json()
    assert "available" in body


def test_session_summary_bahrain(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/race_intelligence/session_summary?session_key=10014")
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is True
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_driver_options(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/race_intelligence/driver_options?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_missing_session_key():
    response = client.get("/api/race_intelligence/session_summary")
    assert response.status_code == 422


def test_strategy_timeline(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/race_intelligence/strategy_timeline?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_pipeline_health(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/race_intelligence/pipeline_health?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)
