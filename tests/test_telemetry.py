import pytest
from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app

client = TestClient(app)


@pytest.fixture
def _override_db(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.clear()


def test_get_telemetry_returns_list(_override_db):
    response = client.get("/api/telemetry?session_key=10014&driver_number=44")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_telemetry_has_required_fields(_override_db):
    response = client.get("/api/telemetry?session_key=10014&driver_number=44")
    data = response.json()
    for row in data:
        assert "date" in row
        assert "speed" in row
        assert "rpm" in row
        assert "n_gear" in row
        assert "throttle" in row
        assert "brake" in row
        assert "drs" in row


def test_get_telemetry_different_driver(_override_db):
    response = client.get("/api/telemetry?session_key=10014&driver_number=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_get_telemetry_empty_for_unknown_driver(_override_db):
    response = client.get("/api/telemetry?session_key=10014&driver_number=99")
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_telemetry_missing_params():
    response = client.get("/api/telemetry")
    assert response.status_code == 422


def test_get_telemetry_speed_is_reasonable(_override_db):
    response = client.get("/api/telemetry?session_key=10014&driver_number=44")
    data = response.json()
    for row in data:
        assert 0 <= row["speed"] <= 400
        assert 0 <= row["rpm"] <= 20000
        assert -1 <= row["n_gear"] <= 8
