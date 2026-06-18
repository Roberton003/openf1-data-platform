"""
Tests for the SLA endpoint /api/pipeline_execution/sla
"""

from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app


def _client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_sla_endpoint_returns_200(mock_db):
    client = next(_client(mock_db))
    response = client.get("/api/pipeline_execution/sla")
    assert response.status_code == 200


def test_sla_endpoint_structure(mock_db_with_sla_columns):
    client = next(_client(mock_db_with_sla_columns))
    response = client.get("/api/pipeline_execution/sla")
    data = response.json()
    assert "total_executions" in data
    assert "breach_count" in data
    assert "breach_rate" in data
    assert "executions" in data
    assert isinstance(data["executions"], list)
    assert len(data["executions"]) >= 1


def test_sla_endpoint_execution_fields(mock_db_with_sla_columns):
    client = next(_client(mock_db_with_sla_columns))
    response = client.get("/api/pipeline_execution/sla")
    data = response.json()
    exec_record = data["executions"][0]
    assert "sla_runtime_status" in exec_record
    assert "sla_quality_status" in exec_record
    assert "sla_freshness_status" in exec_record
    assert exec_record["status"] is not None


def test_sla_endpoint_no_data_returns_404():
    import duckdb

    empty_db = duckdb.connect(":memory:")
    client = next(_client(empty_db))
    response = client.get("/api/pipeline_execution/sla")
    assert response.status_code == 404
    empty_db.close()
