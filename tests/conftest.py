"""
Shared pytest fixtures for the OpenF1 Data Platform test suite.

Centralizes mock database creation, test data generation, and common
utilities so individual test files remain focused on assertions.

Usage:
    # Fixtures are auto-discovered by pytest.
    # Use `@pytest.fixture` name in any test to inject:
    def test_my_endpoint(mock_db):
        ...
"""

import itertools
from typing import Any

import duckdb
import pytest

# ---------------------------------------------------------------------------
# Global cleanup — ensure auth bypass mode for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _cleanup_auth_env():
    """Remove any OPENF1_API_KEY leak between tests."""
    import os

    os.environ.pop("OPENF1_API_KEY", None)
    yield


# ---------------------------------------------------------------------------
# Core database fixture — in-memory DuckDB with mock F1 data
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> duckdb.DuckDBPyConnection:
    """
    Yield an in-memory DuckDB connection pre-populated with minimal F1 mock
    data for API testing. Mirrors the schema contracts in database.py.

    The connection is closed after the test.
    """
    conn = duckdb.connect(database=":memory:")
    _seed_mock_data(conn)
    try:
        yield conn
    finally:
        conn.close()


def _seed_mock_data(conn: duckdb.DuckDBPyConnection) -> None:
    """Populate an in-memory DuckDB with the minimum data set for API tests."""
    # dim_sessions
    conn.execute(
        """
        CREATE TABLE dim_sessions (
            session_key INTEGER, year INTEGER, session_name VARCHAR,
            session_type VARCHAR, circuit_key INTEGER,
            circuit_short_name VARCHAR, country_name VARCHAR
        )
    """
    )
    conn.execute("INSERT INTO dim_sessions VALUES (10014, 2025, 'Race', 'Race', 12, 'Bahrain GP', 'Bahrain')")

    # dim_drivers
    conn.execute(
        """
        CREATE TABLE dim_drivers (
            driver_number INTEGER, full_name VARCHAR, name_acronym VARCHAR,
            team_name VARCHAR, country_code VARCHAR
        )
    """
    )
    conn.execute("INSERT INTO dim_drivers VALUES (44, 'Lewis Hamilton', 'HAM', 'Ferrari', 'GBR')")
    conn.execute("INSERT INTO dim_drivers VALUES (1, 'Max Verstappen', 'VER', 'Red Bull Racing', 'NED')")

    # dim_stints
    conn.execute(
        """
        CREATE TABLE dim_stints (
            session_key INTEGER, driver_number INTEGER, stint_number INTEGER,
            compound VARCHAR, lap_start INTEGER, lap_end INTEGER,
            tyre_age_at_start INTEGER
        )
    """
    )
    conn.execute("INSERT INTO dim_stints VALUES (10014, 44, 1, 'SOFT', 1, 15, 0)")
    conn.execute("INSERT INTO dim_stints VALUES (10014, 1, 1, 'MEDIUM', 1, 18, 0)")

    # fact_car_telemetry
    conn.execute(
        """
        CREATE TABLE fact_car_telemetry (
            session_key INTEGER, driver_number INTEGER, date TIMESTAMP,
            x INTEGER, y INTEGER, z INTEGER,
            speed INTEGER, rpm INTEGER, n_gear INTEGER,
            throttle DOUBLE, brake DOUBLE, drs INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_car_telemetry VALUES "
        "(10014, 44, '2025-03-16 12:00:00.000', 100, 200, 0, 312, 11800, 7, 98.5, 0.0, 12), "
        "(10014, 44, '2025-03-16 12:00:01.000', 110, 210, 0, 315, 12000, 7, 99.0, 0.0, 12), "
        "(10014, 1, '2025-03-16 12:00:00.000', 90, 190, 0, 320, 12100, 8, 100.0, 0.0, 12)"
    )

    # fact_car_location
    conn.execute(
        """
        CREATE TABLE fact_car_location (
            session_key INTEGER, driver_number INTEGER, date TIMESTAMP,
            x INTEGER, y INTEGER, z INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_car_location VALUES "
        "(10014, 44, '2025-03-16 12:00:00.005', 1000, 2000, 100), "
        "(10014, 44, '2025-03-16 12:00:01.005', 1010, 2010, 100), "
        "(10014, 1, '2025-03-16 12:00:00.005', 990, 1990, 100)"
    )

    # fact_intervals
    conn.execute(
        """
        CREATE TABLE fact_intervals (
            session_key INTEGER, driver_number INTEGER,
            gap_to_leader VARCHAR, interval VARCHAR, date TIMESTAMP
        )
    """
    )
    conn.execute("INSERT INTO fact_intervals VALUES (10014, 44, '+2.451s', '+0.150s', '2025-03-16 12:00:01')")

    # fact_pit_stops
    conn.execute(
        """
        CREATE TABLE fact_pit_stops (
            session_key INTEGER, driver_number INTEGER, lap_number INTEGER,
            stop_duration DOUBLE, lane_duration DOUBLE,
            pit_duration DOUBLE, date TIMESTAMP
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_pit_stops VALUES "
        "(10014, 44, 15, 2.3, 16.5, 18.8, '2025-03-16 12:30:00'), "
        "(10014, 1, 14, 2.1, 15.9, 18.0, '2025-03-16 12:28:00')"
    )

    # fact_pipeline_execution
    conn.execute(
        """
        CREATE TABLE fact_pipeline_execution (
            run_id VARCHAR, pipeline_name VARCHAR, session_key INTEGER,
            execution_timestamp TIMESTAMP, duration_seconds DOUBLE,
            status VARCHAR, total_rows_processed INTEGER,
            total_rows_bronze INTEGER, total_rows_silver INTEGER,
            total_rows_quarantine INTEGER, quarantine_rate DOUBLE
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_pipeline_execution VALUES "
        "('uuid-123', 'Silver_Pipeline', 10014, '2026-06-10 13:00:00', "
        "0.29, 'Success', 8520, 10000, 8520, 12, 0.0012)"
    )

    # fact_session_results
    conn.execute(
        """
        CREATE TABLE fact_session_results (
            session_key INTEGER, driver_number INTEGER, position INTEGER,
            points DOUBLE, number_of_laps INTEGER
        )
    """
    )
    conn.execute("INSERT INTO fact_session_results VALUES (10014, 1, 1, 25.0, 57)")

    # dim_weather
    conn.execute(
        """
        CREATE TABLE dim_weather (
            session_key INTEGER, date TIMESTAMP, air_temperature DOUBLE,
            track_temperature DOUBLE, humidity DOUBLE, wind_speed DOUBLE,
            rainfall INTEGER
        )
    """
    )
    conn.execute("INSERT INTO dim_weather VALUES (10014, '2025-03-16 12:00:00.000', 21.5, 31.2, 45.0, 12.0, 0)")

    # fact_race_control
    conn.execute(
        """
        CREATE TABLE fact_race_control (
            session_key INTEGER, driver_number INTEGER, category VARCHAR,
            flag VARCHAR, message VARCHAR, date TIMESTAMP
        )
    """
    )
    conn.execute(
        "INSERT INTO fact_race_control VALUES (10014, 44, 'Flag', 'GREEN', 'Green flag', '2025-03-16 12:05:00.000')"
    )

    # fact_overtakes
    conn.execute(
        """
        CREATE TABLE fact_overtakes (
            session_key INTEGER, overtaking_driver_number INTEGER,
            overtaken_driver_number INTEGER, position INTEGER,
            date TIMESTAMP
        )
    """
    )
    conn.execute("INSERT INTO fact_overtakes VALUES (10014, 1, 44, 1, '2025-03-16 12:10:00.000')")

    # gold_lap_predictions
    conn.execute(
        """
        CREATE TABLE gold_lap_predictions (
            session_key INTEGER, driver_number INTEGER, stint_number INTEGER,
            compound VARCHAR, tyre_age_at_start INTEGER,
            lap_duration_seconds DOUBLE,
            predicted_lap_duration_seconds DOUBLE,
            delta_performance_seconds DOUBLE
        )
    """
    )
    conn.execute("INSERT INTO gold_lap_predictions VALUES (10014, 44, 1, 'SOFT', 0, 92.5, 91.9, 0.6)")

    # fct_f1_telemetry_analysis
    conn.execute(
        """
        CREATE TABLE fct_f1_telemetry_analysis (
            session_key INTEGER, driver_number INTEGER, lap_number INTEGER,
            max_speed INTEGER, avg_speed DOUBLE, max_rpm INTEGER,
            avg_rpm DOUBLE, throttle_intensity_pct DOUBLE,
            brake_intensity_pct DOUBLE, drs_activation_pct DOUBLE,
            gear_changes INTEGER
        )
    """
    )
    conn.execute(
        "INSERT INTO fct_f1_telemetry_analysis VALUES (10014, 44, 1, 312, 280.5, 11800, 11000.0, 98.5, 0.0, 10.0, 15)"
    )


# ---------------------------------------------------------------------------
# Data factory fixtures — generate test data programmatically
# ---------------------------------------------------------------------------

_session_key_seq = itertools.count(20000)
_driver_number_seq = itertools.count(100)


@pytest.fixture
def session_key_factory() -> Any:
    """Return a callable that generates unique test session keys."""
    return lambda: next(_session_key_seq)


@pytest.fixture
def driver_number_factory() -> Any:
    """Return a callable that generates unique test driver numbers."""
    return lambda: next(_driver_number_seq)


@pytest.fixture
def mock_db_with_session(
    mock_db: duckdb.DuckDBPyConnection, session_key_factory: Any
) -> tuple[duckdb.DuckDBPyConnection, int]:
    """
    Return (mock_db, session_key) with an additional session row added
    beyond the default Bahrain seed. Useful for testing multiple sessions.
    """
    session_key = session_key_factory()
    mock_db.execute(
        "INSERT INTO dim_sessions VALUES (?, 2025, 'Race', 'Race', 13, 'Monaco GP', 'Monaco')",
        (session_key,),
    )
    return mock_db, session_key


# ---------------------------------------------------------------------------
# ML model fixtures — synthetic model for deterministic testing
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_model(tmp_path):
    import joblib
    import numpy as np
    from sklearn.linear_model import LinearRegression

    rng = np.random.RandomState(42)
    model = LinearRegression()
    X = rng.rand(100, 5) * 100
    y = 50 + X[:, 0] * 0.5 + rng.rand(100) * 5
    model.fit(X, y)
    model.feature_names_in_ = np.array(
        [
            "throttle_intensity_pct",
            "brake_intensity_pct",
            "tyre_age_at_start",
            "compound_num",
            "max_speed",
        ]
    )
    model_path = tmp_path / "lap_regressor.joblib"
    joblib.dump(model, model_path)
    return model_path


# ---------------------------------------------------------------------------
# Utility fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sql_query_safe():
    """Import the SQL validation function for direct unit testing."""
    from src.web.routers.analytics import _validate_and_prepare_sql

    return _validate_and_prepare_sql


# ---------------------------------------------------------------------------
# MLflow mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mlflow(mocker):
    """Mock mlflow tracking and registry so tests never contact a real server."""
    m = mocker.patch("src.ingestion.assets.mlflow", autospec=True)
    mocker.patch("src.web.model_loader.mlflow", autospec=True)
    return m


# ---------------------------------------------------------------------------
# ChromaDB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chroma_client(tmp_path):
    """Return a chromadb PersistentClient at a temp path."""
    import chromadb

    return chromadb.PersistentClient(path=str(tmp_path / "chromadb"))


@pytest.fixture
def populated_race_control_collection(chroma_client):
    """Return a ChromaDB collection with sample race control messages."""
    collection = chroma_client.get_or_create_collection("race_control")
    collection.add(
        ids=["msg1", "msg2", "msg3"],
        documents=[
            "Green flag on lap 1",
            "Yellow flag due to debris on track",
            "Safety car deployed after crash",
        ],
        metadatas=[
            {"session_key": "10014", "category": "Flag", "flag": "GREEN"},
            {"session_key": "10014", "category": "Flag", "flag": "YELLOW"},
            {"session_key": "10014", "category": "Flag", "flag": "SAFETY_CAR"},
        ],
    )
    return collection


# ---------------------------------------------------------------------------
# Synthetic sklearn model (RandomForest) for MLflow integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_random_forest(tmp_path):
    """Return a synthetic RandomForestRegressor with archetypal feature names."""
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor

    rng = np.random.RandomState(42)
    model = RandomForestRegressor(n_estimators=10, random_state=42, n_jobs=1)
    X = rng.rand(50, 5) * 100
    y = 50 + X[:, 0] * 0.5 + rng.rand(50) * 5
    model.fit(X, y)
    model.feature_names_in_ = np.array(
        [
            "throttle_intensity_pct",
            "brake_intensity_pct",
            "tyre_age_at_start",
            "compound_num",
            "max_speed",
        ]
    )
    path = tmp_path / "lap_regressor.joblib"
    joblib.dump(model, path)
    return path


# ---------------------------------------------------------------------------
# Mock DB with SLA columns (extended schema)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_with_sla_columns(
    mock_db: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyConnection:
    """Return mock_db with SLA columns added to fact_pipeline_execution."""
    mock_db.execute("ALTER TABLE fact_pipeline_execution ADD COLUMN IF NOT EXISTS records_rejected INTEGER")
    mock_db.execute("ALTER TABLE fact_pipeline_execution ADD COLUMN IF NOT EXISTS data_freshness_minutes DOUBLE")
    mock_db.execute("ALTER TABLE fact_pipeline_execution ADD COLUMN IF NOT EXISTS sla_runtime_status VARCHAR")
    mock_db.execute("ALTER TABLE fact_pipeline_execution ADD COLUMN IF NOT EXISTS sla_quality_status VARCHAR")
    mock_db.execute("ALTER TABLE fact_pipeline_execution ADD COLUMN IF NOT EXISTS sla_freshness_status VARCHAR")
    return mock_db
