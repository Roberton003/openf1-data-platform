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
        "INSERT INTO fact_pipeline_execution VALUES "
        "('2026-06-10 13:00:00', 'uuid-123', 'Silver_Pipeline', "
        "0.29, 8520, 8520, 0, 'Success')"
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
