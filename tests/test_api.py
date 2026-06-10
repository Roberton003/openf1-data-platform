import duckdb
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
        "INSERT INTO dim_sessions VALUES (10014, 2025, 'Race', 'Race', 12, 'Bahrain GP', 'Bahrain')"
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
        "INSERT INTO dim_drivers VALUES (44, 'Lewis Hamilton', 'HAM', 'Ferrari', 'GBR')"
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
        "INSERT INTO fact_car_telemetry VALUES (10014, 44, '2025-03-16 12:00:00', 312, 11800, 7, 98.5, 0.0, 12)"
    )

    # 5. Setup mock fact_intervals
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
        "INSERT INTO fact_intervals VALUES (10014, 44, '+2.451s', '+0.150s', '2025-03-16 12:00:01')"
    )

    # 6. Setup mock fact_pit_stops
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
        "INSERT INTO fact_pit_stops VALUES (10014, 44, 15, 2.3, 16.5, 18.8, '2025-03-16 12:30:00')"
    )

    # 7. Setup mock fact_pipeline_execution
    conn.execute(
        """
        CREATE TABLE fact_pipeline_execution (
            execution_timestamp TIMESTAMP,
            run_id VARCHAR,
            pipeline_name VARCHAR,
            duration_seconds DOUBLE,
            rows_bronze INTEGER,
            rows_silver INTEGER,
            rows_quarantine INTEGER,
            status VARCHAR
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_pipeline_execution VALUES ('2026-06-10 13:00:00', 'uuid-123', 'Silver_Pipeline', 0.29, 8520, 8520, 0, 'Success')"
    )

    try:
        yield conn
    finally:
        conn.close()


# Apply overrides
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_read_index_template():
    response = client.get("/")
    assert response.status_code == 200
    assert "OpenF1" in response.text
    assert "Scuderia Ferrari" in response.text


def test_read_observability_template():
    response = client.get("/observabilidade")
    assert response.status_code == 200
    assert "Observabilidade" in response.text


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
    assert len(data) == 1
    assert data[0]["driver_number"] == 44
    assert data[0]["name_acronym"] == "HAM"


def test_get_telemetry():
    response = client.get("/api/telemetry?session_key=10014&driver_number=44")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
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
    assert len(data) == 1
    assert data[0]["driver"] == "HAM"
    assert data[0]["stop_duration"] == 2.3


def test_get_pipeline_execution():
    response = client.get("/api/pipeline_execution")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "uuid-123"
    assert data[0]["status"] == "Success"
