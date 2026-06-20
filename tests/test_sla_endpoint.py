"""
Tests for the SLA endpoint /api/pipeline_execution/sla
"""

import duckdb
import pytest
from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app


@pytest.fixture
def _client(mock_db):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(overrides_before)


@pytest.fixture
def _client_sla(mock_db_with_sla_columns):
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: mock_db_with_sla_columns
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(overrides_before)


def test_sla_endpoint_returns_200(_client):
    response = _client.get("/api/pipeline_execution/sla")
    assert response.status_code == 200


def test_sla_endpoint_structure(_client_sla):
    response = _client_sla.get("/api/pipeline_execution/sla")
    data = response.json()
    assert "total_executions" in data
    assert "breach_count" in data
    assert "breach_rate" in data
    assert "executions" in data
    assert isinstance(data["executions"], list)
    assert len(data["executions"]) >= 1


def test_sla_endpoint_execution_fields(_client_sla):
    response = _client_sla.get("/api/pipeline_execution/sla")
    data = response.json()
    exec_record = data["executions"][0]
    assert "sla_runtime_status" in exec_record
    assert "sla_quality_status" in exec_record
    assert "sla_freshness_status" in exec_record
    assert exec_record["status"] is not None


def test_sla_endpoint_no_data_returns_404():
    empty_db = duckdb.connect(":memory:")
    overrides_before = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: empty_db
    try:
        with TestClient(app) as c:
            response = c.get("/api/pipeline_execution/sla")
            assert response.status_code == 404
    finally:
        empty_db.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_before)
