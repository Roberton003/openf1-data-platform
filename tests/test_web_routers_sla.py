from unittest.mock import patch

import duckdb
import pytest
from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app


@pytest.fixture
def mock_db():
    conn = duckdb.connect(database=":memory:")
    conn.execute(
        """
        CREATE TABLE fact_pipeline_execution (
            run_id VARCHAR,
            pipeline_name VARCHAR,
            session_key INTEGER,
            execution_timestamp TIMESTAMP,
            duration_seconds DOUBLE,
            status VARCHAR,
            total_rows_processed INTEGER,
            total_rows_bronze INTEGER,
            total_rows_silver INTEGER,
            total_rows_quarantine INTEGER,
            quarantine_rate DOUBLE,
            records_rejected INTEGER,
            data_freshness_minutes DOUBLE,
            sla_runtime_status VARCHAR,
            sla_quality_status VARCHAR,
            sla_freshness_status VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO fact_pipeline_execution VALUES
        (
            'run-1',
            'silver',
            10014,
            NOW(),
            42.0,
            'SUCCESS',
            1000,
            1000,
            950,
            5,
            0.005,
            5,
            12.0,
            'COMPLIANT',
            'COMPLIANT',
            'COMPLIANT'
        )
        """
    )
    try:
        yield conn
    finally:
        conn.close()


class TestComputeSlaStatus:
    def test_all_compliant(self):
        from src.web.routers.sla import _compute_sla_status

        result = _compute_sla_status(
            {
                "data_freshness_minutes": 5,
                "duration_seconds": 30,
                "quarantine_rate": 0.0,
            }
        )
        assert result["sla_runtime_status"] == "COMPLIANT"
        assert result["sla_quality_status"] == "COMPLIANT"
        assert result["sla_freshness_status"] == "COMPLIANT"

    def test_runtime_breach(self):
        from src.web.routers.sla import _compute_sla_status

        result = _compute_sla_status(
            {
                "data_freshness_minutes": 5,
                "duration_seconds": 999,
                "quarantine_rate": 0.0,
            }
        )
        assert result["sla_runtime_status"] == "BREACHED"

    def test_quality_breach(self):
        from src.web.routers.sla import _compute_sla_status

        result = _compute_sla_status(
            {
                "data_freshness_minutes": 5,
                "duration_seconds": 30,
                "quarantine_rate": 0.5,
            }
        )
        assert result["sla_quality_status"] == "BREACHED"

    def test_freshness_breach(self):
        from src.web.routers.sla import _compute_sla_status

        result = _compute_sla_status(
            {
                "data_freshness_minutes": 999,
                "duration_seconds": 30,
                "quarantine_rate": 0.0,
            }
        )
        assert result["sla_freshness_status"] == "BREACHED"

    def test_freshness_none(self):
        from src.web.routers.sla import _compute_sla_status

        result = _compute_sla_status(
            {
                "data_freshness_minutes": None,
                "duration_seconds": 30,
                "quarantine_rate": 0.0,
            }
        )
        assert result["sla_freshness_status"] == "BREACHED"


class TestCalcTableFreshness:
    def test_file_exists(self, tmp_path):
        from src.web.routers.sla import _calc_table_freshness

        p = tmp_path / "test.parquet"
        p.write_text("data")
        freshness = _calc_table_freshness(str(p))
        assert freshness is not None
        assert freshness > 0

    def test_file_not_found(self):
        from src.web.routers.sla import _calc_table_freshness

        freshness = _calc_table_freshness("/nonexistent/path/file.parquet")
        assert freshness is None

    def test_directory_with_parquet(self, tmp_path):
        from src.web.routers.sla import _calc_table_freshness

        d = tmp_path / "table_dir"
        d.mkdir()
        (d / "part1.parquet").write_text("data")
        (d / "part2.parquet").write_text("data")
        freshness = _calc_table_freshness(str(d))
        assert freshness is not None
        assert freshness > 0

    def test_empty_directory(self, tmp_path):
        from src.web.routers.sla import _calc_table_freshness

        d = tmp_path / "empty_dir"
        d.mkdir()
        freshness = _calc_table_freshness(str(d))
        assert freshness is None


class TestGetTableSla:
    def test_returns_structure(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with TestClient(app) as c:
            resp = c.get("/api/pipeline_execution/sla/tables")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert "tables" in data
        assert "total_tables" in data
        assert "breached_count" in data
        assert "no_data_count" in data
        assert data["total_tables"] == 3

    def test_no_data_status(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch("src.web.routers.sla._calc_table_freshness", return_value=None):
            with TestClient(app) as c:
                resp = c.get("/api/pipeline_execution/sla/tables")
        app.dependency_overrides.clear()
        data = resp.json()
        assert all(t["status"] == "NO_DATA" for t in data["tables"])
        assert data["no_data_count"] == 3

    def test_breached_status(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch("src.web.routers.sla._calc_table_freshness", return_value=120.0):
            with TestClient(app) as c:
                resp = c.get("/api/pipeline_execution/sla/tables")
        app.dependency_overrides.clear()
        data = resp.json()
        assert all(t["status"] == "BREACHED" for t in data["tables"])
        assert data["breached_count"] == 3

    def test_warning_status(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch("src.web.routers.sla._calc_table_freshness", return_value=45.0):
            with TestClient(app) as c:
                resp = c.get("/api/pipeline_execution/sla/tables")
        app.dependency_overrides.clear()
        data = resp.json()
        assert all(t["status"] == "WARNING" for t in data["tables"])


class TestGetPipelineSla:
    def test_returns_summary(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with TestClient(app) as c:
            resp = c.get("/api/pipeline_execution/sla")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_executions"] == 1
        assert data["breach_count"] == 0
        assert data["avg_freshness_minutes"] == 12.0
        assert len(data["executions"]) == 1
