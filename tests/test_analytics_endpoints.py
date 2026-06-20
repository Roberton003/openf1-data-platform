"""Tests for web/routers/analytics.py — additional endpoints for coverage."""

from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app

client = TestClient(app)


def test_get_sessions(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_drivers(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/drivers?session_key=10014")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_intervals(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/intervals?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_pit_stops(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/pit_stops?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_weather(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/weather?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_stints(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/stints?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_overtakes(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/overtakes?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_pipeline_execution(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/pipeline_execution")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_race_control(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/race_control?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_winner(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/winner?session_key=10014")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_driver_lap_telemetry(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/driver_lap_telemetry?session_key=10014&driver_number=44&lap_number=1")
        assert response.status_code in (200, 404)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_get_session_results(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/session_results?session_key=10014")
        assert response.status_code in (200, 404)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)


def test_sql_gateway_empty_query():
    response = client.post("/api/analytics/query", json={"query": ""})
    assert response.status_code == 400


def test_sql_gateway_invalid_query():
    response = client.post("/api/analytics/query", json={"query": "DROP TABLE x"})
    assert response.status_code in (400, 403)
