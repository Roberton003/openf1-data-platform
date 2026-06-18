import pytest
from fastapi.testclient import TestClient

from src.web.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _patch_data_dir(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr("src.web.health._base_data_dir", lambda: str(data_dir))
    silver = data_dir / "silver"
    silver.mkdir()
    (silver / "dim_sessions.parquet").write_text("mock")
    (silver / "dim_drivers.parquet").write_text("mock")
    return data_dir


def test_health_returns_healthy():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "check" in body


def test_readiness_returns_ready():
    response = client.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "duckdb" in body["checks"]
    assert "required_files" in body["checks"]
    assert "freshness" in body["checks"]


def test_readiness_fails_when_files_missing(monkeypatch, tmp_path):
    empty_dir = tmp_path / "emptydata"
    empty_dir.mkdir()
    monkeypatch.setattr("src.web.health._base_data_dir", lambda: str(empty_dir))
    response = client.get("/api/ready")
    assert response.status_code == 503
    body = response.json()
    assert "not_ready" in str(body["detail"]["status"])


def test_readiness_reports_freshness():
    response = client.get("/api/ready")
    body = response.json()
    freshness = body["checks"]["freshness"]
    for layer in ("bronze", "silver", "gold"):
        assert layer in freshness
