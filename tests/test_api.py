import duckdb
import pytest
from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app


# Override get_db dependency with a mock database in memory for testing
def override_get_db():
    conn = duckdb.connect(database=":memory:")

    # 1. Setup mock dim_sessions
    conn.execute(
        """
        CREATE TABLE dim_sessions (
            session_key INTEGER,
            year INTEGER,
            session_name VARCHAR,
            session_type VARCHAR,
            circuit_key INTEGER,
            circuit_short_name VARCHAR,
            country_name VARCHAR
        )
    """
    )
    conn.execute(
        "INSERT INTO dim_sessions VALUES "
        "(10014, 2025, 'Race', 'Race', 12, 'Bahrain GP', 'Bahrain')"
    )

    # 2. Setup mock dim_drivers
    conn.execute(
        """
        CREATE TABLE dim_drivers (
            driver_number INTEGER,
            full_name VARCHAR,
            name_acronym VARCHAR,
            team_name VARCHAR,
            country_code VARCHAR
        )
    """
    )
    conn.execute(
        "INSERT INTO dim_drivers VALUES "
        "(44, 'Lewis Hamilton', 'HAM', 'Ferrari', 'GBR')"
    )
    conn.execute(
        "INSERT INTO dim_drivers VALUES "
        "(1, 'Max Verstappen', 'VER', 'Red Bull Racing', 'NED')"
    )

    # 3. Setup mock dim_stints
    conn.execute(
        """
        CREATE TABLE dim_stints (
            session_key INTEGER,
            driver_number INTEGER,
            stint_number INTEGER,
            compound VARCHAR,
            lap_start INTEGER,
            lap_end INTEGER,
            tyre_age_at_start INTEGER
        )
    """
    )
    conn.execute("INSERT INTO dim_stints VALUES (10014, 44, 1, 'SOFT', 1, 15, 0)")
    conn.execute("INSERT INTO dim_stints VALUES (10014, 1, 1, 'MEDIUM', 1, 18, 0)")

    # 4. Setup mock fact_car_telemetry
    conn.execute(
        """
        CREATE TABLE fact_car_telemetry (
            session_key INTEGER,
            driver_number INTEGER,
            date TIMESTAMP,
            speed INTEGER,
            rpm INTEGER,
            n_gear INTEGER,
            throttle DOUBLE,
            brake DOUBLE,
            drs INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_car_telemetry VALUES "
        "(10014, 44, '2025-03-16 12:00:00.000', 312, 11800, 7, 98.5, 0.0, 12)"
    )
    conn.execute(
        "INSERT INTO fact_car_telemetry VALUES "
        "(10014, 44, '2025-03-16 12:00:01.000', 315, 12000, 7, 99.0, 0.0, 12)"
    )
    conn.execute(
        "INSERT INTO fact_car_telemetry VALUES "
        "(10014, 1, '2025-03-16 12:00:00.000', 320, 12100, 8, 100.0, 0.0, 12)"
    )

    # 5. Setup mock fact_car_location
    conn.execute(
        """
        CREATE TABLE fact_car_location (
            session_key INTEGER,
            driver_number INTEGER,
            date TIMESTAMP,
            x INTEGER,
            y INTEGER,
            z INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_car_location VALUES "
        "(10014, 44, '2025-03-16 12:00:00.005', 1000, 2000, 100)"
    )
    conn.execute(
        "INSERT INTO fact_car_location VALUES "
        "(10014, 44, '2025-03-16 12:00:01.005', 1010, 2010, 100)"
    )
    conn.execute(
        "INSERT INTO fact_car_location VALUES "
        "(10014, 1, '2025-03-16 12:00:00.005', 990, 1990, 100)"
    )

    # 6. Setup mock fact_intervals
    conn.execute(
        """
        CREATE TABLE fact_intervals (
            session_key INTEGER,
            driver_number INTEGER,
            gap_to_leader VARCHAR,
            interval VARCHAR,
            date TIMESTAMP
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_intervals VALUES "
        "(10014, 44, '+2.451s', '+0.150s', '2025-03-16 12:00:01')"
    )

    # 7. Setup mock fact_pit_stops
    conn.execute(
        """
        CREATE TABLE fact_pit_stops (
            session_key INTEGER,
            driver_number INTEGER,
            lap_number INTEGER,
            stop_duration DOUBLE,
            lane_duration DOUBLE,
            pit_duration DOUBLE,
            date TIMESTAMP
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_pit_stops VALUES "
        "(10014, 44, 15, 2.3, 16.5, 18.8, '2025-03-16 12:30:00')"
    )
    conn.execute(
        "INSERT INTO fact_pit_stops VALUES "
        "(10014, 1, 14, 2.1, 15.9, 18.0, '2025-03-16 12:28:00')"
    )

    # 8. Setup mock fact_pipeline_execution
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
            quarantine_rate DOUBLE
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_pipeline_execution VALUES "
        "('uuid-123', 'Silver_Pipeline', 10014, '2026-06-10 13:00:00', "
        "0.29, 'Success', 8520, 10000, 8520, 12, 0.0012)"
    )

    # 9. Setup mock fact_session_results
    conn.execute(
        """
        CREATE TABLE fact_session_results (
            session_key INTEGER,
            driver_number INTEGER,
            position INTEGER,
            points DOUBLE,
            number_of_laps INTEGER
        )
    """
    )
    conn.execute("INSERT INTO fact_session_results VALUES " "(10014, 1, 1, 25.0, 57)")

    # 10. Setup mock dim_weather
    conn.execute(
        """
        CREATE TABLE dim_weather (
            session_key INTEGER,
            date TIMESTAMP,
            air_temperature DOUBLE,
            track_temperature DOUBLE,
            humidity DOUBLE,
            wind_speed DOUBLE,
            rainfall INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO dim_weather VALUES "
        "(10014, '2025-03-16 12:00:00.000', 21.5, 31.2, 45.0, 12.0, 0)"
    )

    # 11. Setup mock fact_race_control
    conn.execute(
        """
        CREATE TABLE fact_race_control (
            session_key INTEGER,
            driver_number INTEGER,
            category VARCHAR,
            flag VARCHAR,
            message VARCHAR,
            date TIMESTAMP
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_race_control VALUES "
        "(10014, 44, 'Flag', 'GREEN', 'Green flag', '2025-03-16 12:05:00.000')"
    )

    # 12. Setup mock fact_overtakes
    conn.execute(
        """
        CREATE TABLE fact_overtakes (
            session_key INTEGER,
            overtaking_driver_number INTEGER,
            overtaken_driver_number INTEGER,
            position INTEGER,
            date TIMESTAMP
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_overtakes VALUES "
        "(10014, 1, 44, 1, '2025-03-16 12:10:00.000')"
    )

    # 13. Setup mock gold_lap_predictions
    conn.execute(
        """
        CREATE TABLE gold_lap_predictions (
            session_key INTEGER,
            driver_number INTEGER,
            stint_number INTEGER,
            compound VARCHAR,
            tyre_age_at_start INTEGER,
            lap_duration_seconds DOUBLE,
            predicted_lap_duration_seconds DOUBLE,
            delta_performance_seconds DOUBLE
        )
    """
    )
    conn.execute(
        "INSERT INTO gold_lap_predictions VALUES "
        "(10014, 44, 1, 'SOFT', 0, 92.5, 91.9, 0.6)"
    )

    # 14. Setup mock fct_f1_telemetry_analysis
    conn.execute(
        """
        CREATE TABLE fct_f1_telemetry_analysis (
            session_key INTEGER,
            driver_number INTEGER,
            lap_number INTEGER,
            max_speed INTEGER,
            avg_speed DOUBLE,
            max_rpm INTEGER,
            avg_rpm DOUBLE,
            throttle_intensity_pct DOUBLE,
            brake_intensity_pct DOUBLE,
            drs_activation_pct DOUBLE,
            gear_changes INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO fct_f1_telemetry_analysis VALUES "
        "(10014, 44, 1, 312, 280.5, 11800, 11000.0, 98.5, 0.0, 10.0, 15)"
    )

    try:
        yield conn
    finally:
        conn.close()


# Apply overrides
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_get_sessions():
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_key"] == 10014
    assert data[0]["country_name"] == "Bahrain"


def test_get_drivers():
    response = client.get("/api/drivers?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["driver_number"] == 44
    assert data[0]["name_acronym"] == "HAM"


def test_get_telemetry():
    response = client.get("/api/telemetry?session_key=10014&driver_number=44")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["speed"] == 312
    assert data[0]["rpm"] == 11800


def test_get_intervals():
    response = client.get("/api/intervals?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["driver"] == "HAM"
    assert data[0]["gap_to_leader"] == "+2.451s"


def test_get_pit_stops():
    response = client.get("/api/pit_stops?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Ordered by lap_number ASC, pit_duration DESC
    assert data[0]["driver"] == "VER"
    assert data[0]["stop_duration"] == 2.1
    assert data[1]["driver"] == "HAM"
    assert data[1]["stop_duration"] == 2.3


def test_get_pipeline_execution():
    response = client.get("/api/pipeline_execution")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "uuid-123"
    assert data[0]["status"] == "Success"
    assert data[0]["total_rows_quarantine"] == 12


def test_get_lap_predictions():
    response = client.get(
        "/api/predictions/lap_time?session_key=10014&driver_number=44"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["predicted_lap_time"] == 91.9


def test_get_weather():
    response = client.get("/api/weather?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["air_temperature"] == 21.5
    assert data[0]["humidity"] == 45.0


def test_get_stints():
    response = client.get("/api/stints?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["driver"] == "HAM"
    assert data[0]["compound"] == "SOFT"
    assert data[1]["driver"] == "VER"
    assert data[1]["compound"] == "MEDIUM"


def test_get_race_control():
    response = client.get("/api/race_control?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["driver"] == "HAM"
    assert data[0]["flag"] == "GREEN"
    assert data[0]["message"] == "Green flag"


def test_get_winner():
    response = client.get("/api/winner?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["driver"] == "VER"
    assert data[0]["position"] == 1


def test_get_duel_location():
    response = client.get("/api/duel/location?session_key=10014&driver_number=44")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["x"] == 1000
    assert data[0]["y"] == 2000
    assert data[0]["speed"] == 312
    assert data[0]["gear"] == 7


def test_get_duel_metrics():
    response = client.get("/api/duel/metrics?session_key=10014&driver_1=44&driver_2=1")
    assert response.status_code == 200
    data = response.json()
    assert "44" in data
    assert "1" in data
    assert data["44"]["max_speed"] == 315
    assert data["1"]["max_speed"] == 320
    assert data["44"]["best_pit"] == 18.8
    assert data["1"]["best_pit"] == 18.0


def test_get_overtakes():
    response = client.get("/api/overtakes?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["overtaking_driver"] == "VER"
    assert data[0]["overtaken_driver"] == "HAM"
    assert data[0]["position"] == 1


def test_execute_adhoc_query_success():
    response = client.post(
        "/api/analytics/query",
        json={
            "query": "SELECT session_key, country_name FROM dim_sessions ORDER BY session_key"
        },
    )
    assert response.status_code == 200
    data = response.json()
    # New contract: {columns, row_count, total_rows, truncated, limit, data}
    assert data["columns"] == ["session_key", "country_name"]
    assert data["row_count"] == 1
    assert data["truncated"] is False
    assert data["limit"] == 10_000
    assert len(data["data"]) == 1
    assert data["data"][0]["session_key"] == 10014
    assert data["data"][0]["country_name"] == "Bahrain"


def test_execute_adhoc_query_forbidden():
    response = client.post(
        "/api/analytics/query",
        json={"query": "DROP TABLE dim_sessions"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Apenas consultas de leitura" in data["detail"]


# ---------------------------------------------------------------------------
# SQL Injection / Hardened Gateway Tests (Sprint 1.1 + 1.2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious_query,expected_fragment",
    [
        # Plain DDL/DML — blocked by allowlist (must start with SELECT/WITH)
        ("DROP TABLE dim_sessions", "Apenas consultas de leitura"),
        ("DELETE FROM dim_sessions", "Apenas consultas de leitura"),
        ("INSERT INTO dim_sessions VALUES (1)", "Apenas consultas de leitura"),
        ("UPDATE dim_sessions SET year=2000", "Apenas consultas de leitura"),
        ("CREATE TABLE x (a INT)", "Apenas consultas de leitura"),
        ("ALTER TABLE dim_sessions ADD COLUMN x INT", "Apenas consultas de leitura"),
        ("TRUNCATE dim_sessions", "Apenas consultas de leitura"),
        # Mixed-case obfuscation — still blocked by first-token allowlist
        ("DrOp TABLE dim_sessions", "Apenas consultas de leitura"),
        ("  DROP TABLE dim_sessions", "Apenas consultas de leitura"),
        ("select * from dim_sessions; DROP TABLE dim_sessions", "Token proibido"),
        # Dangerous tokens inside CTE/subquery — blocked by word-boundary regex
        (
            "WITH x AS (SELECT * FROM dim_sessions) SELECT * FROM x; DROP TABLE y",
            "Token proibido",
        ),
        (
            "SELECT * FROM dim_sessions WHERE country_name = 'SELECT'; DELETE FROM dim_sessions",
            "Token proibido",
        ),
        # SQL Server-style stacked queries — blocked
        ("SELECT * FROM dim_sessions; DROP TABLE dim_sessions", "Token proibido"),
        # UNION-based exfiltration with DDL — blocked
        (
            "SELECT * FROM dim_sessions UNION ALL SELECT 1; DROP TABLE t",
            "Token proibido",
        ),
        # DuckDB-specific export/write functions — blocked
        (
            "SELECT * FROM dim_sessions; COPY (SELECT 1) TO '/tmp/x.csv'",
            "Token proibido",
        ),
        ("SELECT * FROM dim_sessions; EXPORT DATABASE '/tmp/db'", "Token proibido"),
        # Comment-stripping bypass — comment containing blocked token stripped
        (
            "SELECT /* DROP */ * FROM dim_sessions",
            None,
        ),  # safe — token removed with comment
        (
            "SELECT * FROM dim_sessions -- DROP TABLE",
            None,
        ),  # safe — token in line comment stripped
        # String-literal bypass — token inside string literal should be fine
        ("SELECT * FROM dim_sessions WHERE country_name = 'drop off'", None),
        # Empty query
        ("", "Query vazia"),
        ("   ", "Query vazia"),
        # Non-SELECT/WITH first token
        ("SHOW TABLES", "Apenas consultas de leitura"),
        ("PRAGMA table_info('dim_sessions')", "Apenas consultas de leitura"),
        ("EXPLAIN SELECT * FROM dim_sessions", "Apenas consultas de leitura"),
        ("SET threads = 8", "Apenas consultas de leitura"),
    ],
)
def test_sql_gateway_injection_blocked(malicious_query, expected_fragment):
    response = client.post(
        "/api/analytics/query",
        json={"query": malicious_query},
    )
    if expected_fragment is None:
        # Query is allowed (safe) — should not return 400 for security reasons
        # (may still return 400 if table doesn't exist, which is acceptable)
        if response.status_code == 400:
            # Verify the error is NOT a security rejection
            detail = response.json().get("detail", "")
            assert "Apenas consultas de leitura" not in detail
            assert "Token proibido" not in detail
            assert "Query vazia" not in detail
    else:
        assert response.status_code == 400
        data = response.json()
        assert expected_fragment in data["detail"]


def test_sql_gateway_limit_injection():
    """Queries without LIMIT should have one auto-injected."""
    response = client.post(
        "/api/analytics/query",
        json={"query": "SELECT * FROM dim_sessions"},
    )
    assert response.status_code == 200
    data = response.json()
    # The endpoint returns the structured envelope
    assert "limit" in data
    assert data["limit"] == 10_000


def test_sql_gateway_preserves_explicit_limit():
    """Queries with explicit LIMIT should not be modified."""
    response = client.post(
        "/api/analytics/query",
        json={"query": "SELECT * FROM dim_sessions LIMIT 5"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 1  # Mock only has 1 row; LIMIT 5 is respected


def test_execute_chat_query_success():
    response = client.post(
        "/api/analytics/chat",
        json={"session_key": 10014, "question": "Green flag event"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "relevance" in data
    assert data["relevance"] > 0.05
    assert "Green flag" in data["data"]["message"]


def test_execute_chat_query():
    response = client.post(
        "/api/analytics/chat",
        json={"session_key": 10014, "question": "Rain or water on track"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "relevance" in data
    assert isinstance(data["relevance"], float)


def test_get_telemetry_analysis():
    response = client.get(
        "/api/analytics/telemetry_analysis?session_key=10014&driver_number=44"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_key"] == 10014
    assert data[0]["driver_number"] == 44
    assert data[0]["lap_number"] == 1
    assert data[0]["max_speed"] == 312
    assert data[0]["gear_changes"] == 15


def test_race_intelligence_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Race Intelligence" in response.text


def test_race_intelligence_session_summary_contract():
    response = client.get("/api/race_intelligence/session_summary?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["reason"] == "ok"
    assert data["data"]["session"]["country_name"] == "Bahrain"
    assert data["data"]["winner"]["driver"] == "VER"
    assert data["data"]["driver_count"] == 2
    assert data["data"]["gold_predictions_available"] is True


def test_race_intelligence_session_summary_empty_state():
    response = client.get("/api/race_intelligence/session_summary?session_key=999")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["reason"] == "no_rows_for_session"
    assert data["data"] is None
    assert data["metadata"]["empty_state"]["reason"] == "no_rows_for_session"


def test_race_intelligence_driver_options_contract():
    response = client.get("/api/race_intelligence/driver_options?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["reason"] == "ok"
    assert len(data["data"]) == 2
    assert data["data"][0]["driver_number"] == 44
    assert data["data"][0]["has_telemetry"] is True


def test_race_intelligence_strategy_timeline_contract():
    response = client.get("/api/race_intelligence/strategy_timeline?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    event_types = {event["event_type"] for event in data["data"]}
    assert {"race_control", "pit_stop", "overtake"}.issubset(event_types)
    assert all("source" in event for event in data["data"])


def test_race_intelligence_pipeline_health_contract():
    response = client.get("/api/race_intelligence/pipeline_health?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["reason"] == "ok"
    assert data["data"]["latest_execution"]["run_id"] == "uuid-123"
    assert data["data"]["health_status"] == "healthy"


def test_race_intelligence_prediction_status_contract():
    response = client.get("/api/race_intelligence/prediction_status?session_key=10014")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["reason"] == "ok"
    assert data["data"]["prediction_count"] == 1
    assert data["data"]["driver_count"] == 1


def test_race_intelligence_driver_duel_contract():
    response = client.get(
        "/api/race_intelligence/driver_duel?session_key=10014&driver_1=44&driver_2=1"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["reason"] == "ok"
    assert data["data"]["drivers"]["44"]["max_speed"] == 315
    assert data["data"]["drivers"]["1"]["max_speed"] == 320


# ---------------------------------------------------------------------------
# Health / Readiness Endpoint Tests (Sprint 1.3)
# ---------------------------------------------------------------------------


def test_health_check_liveness():
    """Liveness probe should return 200 with status=healthy."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["check"] == "duckdb_responsive"


def test_readiness_check_returns_checks_structure():
    """Readiness probe should return checks for duckdb, files, and freshness."""
    # In test environment, the data/ directory may not have the parquet files
    # so this may return 503. We only assert the response shape.
    response = client.get("/api/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    if response.status_code == 200:
        assert data["status"] == "ready"
        assert "checks" in data
        assert "duckdb" in data["checks"]
        assert "required_files" in data["checks"]
        assert "freshness" in data["checks"]
        assert "timestamp_epoch" in data
    else:
        # Not ready — checks should explain why
        assert data["detail"]["status"] == "not_ready"
        assert "checks" in data["detail"]


def test_health_check_duckdb_always_responsive():
    """DuckDB should be responsive in in-memory mode."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_request_id_header_returned():
    """Every response should include X-Request-ID header."""
    response = client.get("/api/sessions")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_request_id_header_propagated_from_client():
    """If client passes X-Request-ID, it should be echoed back."""
    custom_id = "test-trace-abc123"
    response = client.get("/api/sessions", headers={"X-Request-ID": custom_id})
    assert response.headers["x-request-id"] == custom_id


# ---------------------------------------------------------------------------
# Negative API Tests — 404, 422, 500, schema validation (Sprint 1.5 / 3.3)
# ---------------------------------------------------------------------------


def test_nonexistent_endpoint_returns_404():
    """Requesting an unknown endpoint should return 404, not crash."""
    response = client.get("/api/nonexistent_route")
    assert response.status_code == 404


def test_missing_required_query_param_returns_422():
    """Endpoints requiring query params should return 422 on missing param."""
    response = client.get("/api/drivers")
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_invalid_session_key_type_returns_422():
    """Non-integer session_key should return 422 validation error."""
    response = client.get("/api/drivers?session_key=not_a_number")
    assert response.status_code == 422


def test_empty_query_body_returns_422():
    """Empty JSON body to /api/analytics/query should return 422."""
    response = client.post("/api/analytics/query", json={})
    assert response.status_code == 422


def test_empty_query_string_returns_400():
    """Empty query string should be rejected by SQL gateway."""
    response = client.post("/api/analytics/query", json={"query": ""})
    assert response.status_code == 400


def test_syntax_error_in_sql_returns_400():
    """Malformed SQL should return 400 with helpful error."""
    response = client.post(
        "/api/analytics/query",
        json={"query": "SELECT * FRMO nowhere"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    # Either a DuckDB syntax error or another parser error is acceptable
    assert len(detail) > 10


def test_query_on_nonexistent_table_returns_400():
    """Querying a table that doesn't exist should return 400, not 500."""
    response = client.post(
        "/api/analytics/query",
        json={"query": "SELECT * FROM completely_made_up_table"},
    )
    assert response.status_code == 400


def test_session_without_data_returns_empty():
    """Session 99999 doesn't exist — endpoints should return [], not error."""
    response = client.get("/api/drivers?session_key=99999")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_weather_without_session_returns_empty():
    """Weather for non-existent session should return empty, not crash."""
    response = client.get("/api/weather?session_key=99999")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_race_control_without_session_returns_empty():
    """Race control for non-existent session should return empty."""
    response = client.get("/api/race_control?session_key=99999")
    assert response.status_code == 200
    assert response.json() == []


def test_pit_stops_without_session_returns_empty():
    """Pit stops for non-existent session should return empty."""
    response = client.get("/api/pit_stops?session_key=99999")
    assert response.status_code == 200
    assert response.json() == []


def test_overtakes_without_session_returns_empty():
    """Overtakes for non-existent session should return empty."""
    response = client.get("/api/overtakes?session_key=99999")
    assert response.status_code == 200
    assert response.json() == []


def test_duel_with_missing_driver_returns_empty_or_404():
    """Duel endpoint with non-existent driver should not crash (500)."""
    response = client.get("/api/duel/location?session_key=99999&driver_number=999")
    assert response.status_code == 200
    # Either returns empty data or an empty state
    data = response.json()
    assert isinstance(data, list) or isinstance(data, dict)


def test_chat_missing_session_in_payload_returns_422():
    """Chat endpoint without session_key in payload should return 422."""
    response = client.post("/api/analytics/chat", json={"question": "test"})
    assert response.status_code == 422


def test_chat_missing_question_in_payload_returns_422():
    """Chat endpoint without question in payload should return 422."""
    response = client.post("/api/analytics/chat", json={"session_key": 10014})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Unit tests for TTLCache and SQL validation helper
# ---------------------------------------------------------------------------


def test_ttlcache_returns_cached_value():
    """TTLCache should return cached value on subsequent calls."""
    from src.web.database import TTLCache

    cache = TTLCache(maxsize=10, ttl_seconds=60)
    call_count = 0

    @cache
    def expensive(conn, x):
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call — cache miss
    result1 = expensive("fake_conn", 5)
    assert result1 == 10
    assert call_count == 1

    # Second call with same args — cache hit
    result2 = expensive("fake_conn", 5)
    assert result2 == 10
    assert call_count == 1  # Not called again

    # Different args — cache miss
    result3 = expensive("fake_conn", 7)
    assert result3 == 14
    assert call_count == 2


def test_ttlcache_exclude_first_arg_from_key():
    """TTLCache should exclude first arg (connection) from cache key."""
    from src.web.database import TTLCache

    cache = TTLCache(maxsize=10, ttl_seconds=60)
    call_count = 0

    @cache
    def func(conn, value):
        nonlocal call_count
        call_count += 1
        return value

    # Different "connections" but same query params → should hit cache
    func("conn_a", 42)
    assert call_count == 1
    func("conn_b", 42)
    assert call_count == 1  # Cache hit despite different first arg


def test_ttlcache_evicts_oldest_when_full():
    """TTLCache should evict oldest entry when at maxsize."""
    from src.web.database import TTLCache

    cache = TTLCache(maxsize=2, ttl_seconds=60)
    call_count = 0

    @cache
    def func(conn, x):
        nonlocal call_count
        call_count += 1
        return x

    func("c", 1)  # cache: [1]
    func("c", 2)  # cache: [1, 2]
    func("c", 3)  # cache: [2, 3] (1 evicted)
    assert call_count == 3

    # Re-querying 1 should miss (was evicted)
    func("c", 1)
    assert call_count == 4


def test_sql_validation_helper_allowlist(sql_query_safe):
    """Test the SQL validation helper directly from conftest fixture."""
    from fastapi import HTTPException

    # Valid queries — should pass and return a valid string
    result = sql_query_safe("SELECT * FROM t")
    assert "SELECT" in result.upper()

    result = sql_query_safe("WITH x AS (SELECT 1) SELECT * FROM x")
    assert "WITH" in result.upper()

    # Invalid — should raise
    with pytest.raises(HTTPException) as exc_info:
        sql_query_safe("DROP TABLE t")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        sql_query_safe("")
    assert exc_info.value.status_code == 400
