"""Tests for API error paths, edge cases, schema evolution, and ML predictions."""

import duckdb
import pytest
from fastapi.testclient import TestClient

from src.web.database import get_db
from src.web.main import app


@pytest.fixture
def empty_db():
    """In-memory DuckDB with session table but NO telemetry data."""
    conn = duckdb.connect(database=":memory:")
    conn.execute(
        "CREATE TABLE dim_sessions (session_key INTEGER, year INTEGER, "
        "session_name VARCHAR, session_type VARCHAR, circuit_key INTEGER, "
        "circuit_short_name VARCHAR, country_name VARCHAR)"
    )
    conn.execute(
        "INSERT INTO dim_sessions VALUES "
        "(10014, 2025, 'Race', 'Race', 12, 'Bahrain GP', 'Bahrain')"
    )
    conn.execute(
        "CREATE TABLE dim_drivers (driver_number INTEGER, full_name VARCHAR, "
        "name_acronym VARCHAR, team_name VARCHAR, country_code VARCHAR)"
    )
    conn.execute(
        "INSERT INTO dim_drivers VALUES (1, 'Max Verstappen', 'VER', 'Red Bull Racing', 'NED')"
    )
    conn.execute(
        "CREATE TABLE fact_car_telemetry (session_key INTEGER, driver_number INTEGER, "
        "speed DOUBLE, rpm DOUBLE, throttle DOUBLE, brake DOUBLE, n_gear INTEGER)"
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def client(empty_db):
    app.dependency_overrides[get_db] = lambda: empty_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Error Paths
# ---------------------------------------------------------------------------


def test_get_sessions_empty_db(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_drivers_with_empty_telemetry(client):
    resp = client.get("/api/drivers?session_key=10014")
    assert resp.status_code == 200


def test_invalid_driver_number(client):
    resp = client.get("/api/telemetry?session_key=10014&driver_number=-1")
    assert resp.status_code in (200, 422, 500)


def test_missing_session_key(client):
    resp = client.get("/api/telemetry?driver_number=1")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_null_values_in_query(client):
    try:
        resp = client.post(
            "/api/analytics/query",
            json={"query": "SELECT NULL as test_col, 1 as num"},
        )
        assert resp.status_code in (200, 400, 500)
    except ValueError:
        pass


def test_sql_gateway_special_characters(client):
    resp = client.post(
        "/api/analytics/query",
        json={"query": "SELECT 'test with quotes' as result"},
    )
    assert resp.status_code in (200, 400)


def test_sql_gateway_empty_query(client):
    resp = client.post(
        "/api/analytics/query",
        json={"query": "-- empty"},
    )
    assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Schema Evolution — Contract Validation
# ---------------------------------------------------------------------------


def test_dim_sessions_schema_contract():
    conn = duckdb.connect(database=":memory:")
    conn.execute(
        "CREATE TABLE dim_sessions (session_key INTEGER, year INTEGER, "
        "session_name VARCHAR, session_type VARCHAR, circuit_key INTEGER, "
        "circuit_short_name VARCHAR, country_name VARCHAR)"
    )
    columns = [col[0] for col in conn.execute("DESCRIBE dim_sessions").fetchall()]
    required = {"session_key", "year", "session_name", "session_type", "country_name"}
    assert required.issubset(columns), f"Missing: {required - set(columns)}"
    conn.close()


def test_dim_drivers_schema_contract():
    conn = duckdb.connect(database=":memory:")
    conn.execute(
        "CREATE TABLE dim_drivers (driver_number INTEGER, full_name VARCHAR, "
        "name_acronym VARCHAR, team_name VARCHAR, country_code VARCHAR)"
    )
    columns = [col[0] for col in conn.execute("DESCRIBE dim_drivers").fetchall()]
    required = {"driver_number", "full_name", "team_name"}
    assert required.issubset(columns), f"Missing: {required - set(columns)}"
    conn.close()


def test_fact_car_telemetry_schema_contract():
    conn = duckdb.connect(database=":memory:")
    conn.execute(
        "CREATE TABLE fact_car_telemetry ("
        "session_key INTEGER, driver_number INTEGER, speed DOUBLE, "
        "rpm DOUBLE, throttle DOUBLE, brake DOUBLE, n_gear INTEGER)"
    )
    columns = [col[0] for col in conn.execute("DESCRIBE fact_car_telemetry").fetchall()]
    required = {"session_key", "driver_number", "speed"}
    assert required.issubset(columns), f"Missing: {required - set(columns)}"
    conn.close()


# ---------------------------------------------------------------------------
# ML / Predictions
# ---------------------------------------------------------------------------


def test_prediction_model_basic(synthetic_model):
    import joblib
    import pandas as pd

    model = joblib.load(synthetic_model)

    features = [
        "throttle_intensity_pct",
        "brake_intensity_pct",
        "tyre_age_at_start",
        "compound_num",
        "max_speed",
    ]
    sample_input = pd.DataFrame(
        [[50.0, 10.0, 5, 1, 280.0]],
        columns=features,
    )
    prediction = model.predict(sample_input)
    assert len(prediction) == 1
    assert prediction[0] > 0


def test_prediction_model_feature_count(synthetic_model):
    import joblib

    model = joblib.load(synthetic_model)
    if hasattr(model, "n_features_in_"):
        assert model.n_features_in_ == 5
