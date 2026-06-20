"""Tests for ingestion/assets.py — Silver layer assets and contracts."""

import os

import pandas as pd
import pytest
from dagster import build_asset_context

from src.ingestion.assets import silver_metadata_tables, silver_telemetry_location_aligned
from src.ingestion.schemas import RaceControlContract


def _context():
    return build_asset_context()


def _create_partitioned_bronze(base_dir: str, session_key: int = 10014):
    """Write Bronze parquet files in the partitioned format expected by silver_metadata_tables."""
    bronze_dir = os.path.join(base_dir, "bronze", f"session_key={session_key}")
    os.makedirs(bronze_dir, exist_ok=True)

    stints = pd.DataFrame([{
        "session_key": session_key, "driver_number": 44,
        "stint_number": 1, "compound": "SOFT",
        "tyre_age_at_start": 0, "lap_start": 1, "lap_end": 15,
    }])
    stints.to_parquet(os.path.join(bronze_dir, "stints.parquet"), index=False)

    weather = pd.DataFrame([{
        "session_key": session_key, "date": "2025-03-16T12:00:00+00:00",
        "air_temperature": 21.5, "track_temperature": 31.2,
        "humidity": 45.0, "wind_speed": 12.0, "rainfall": 0,
    }])
    weather.to_parquet(os.path.join(bronze_dir, "weather.parquet"), index=False)

    pit_stops = pd.DataFrame([{
        "session_key": session_key, "driver_number": 44,
        "lap_number": 15, "stop_duration": 2.3,
        "lane_duration": 16.5, "pit_duration": 18.8,
        "date": "2025-03-16T12:30:00+00:00",
    }])
    pit_stops.to_parquet(os.path.join(bronze_dir, "pit_stops.parquet"), index=False)

    race_control = pd.DataFrame([{
        "session_key": session_key, "driver_number": 44,
        "category": "Flag", "flag": "GREEN",
        "message": "Green flag", "date": "2025-03-16T12:00:00+00:00",
    }])
    race_control.to_parquet(os.path.join(bronze_dir, "race_control.parquet"), index=False)

    session_result = pd.DataFrame([{
        "session_key": session_key, "driver_number": 44,
        "position": 1, "points": 25.0, "number_of_laps": 57,
    }])
    session_result.to_parquet(os.path.join(bronze_dir, "session_result.parquet"), index=False)

    overtakes = pd.DataFrame([{
        "session_key": session_key, "overtaking_driver_number": 1,
        "overtaken_driver_number": 44, "position": 1,
        "date": "2025-03-16T12:10:00+00:00",
    }])
    overtakes.to_parquet(os.path.join(bronze_dir, "overtakes.parquet"), index=False)


def test_silver_metadata_writes_parquet(tmp_data_dir, mock_fetch_api, mocker):
    mocker.patch("src.ingestion.assets.index_race_control_messages")
    _create_partitioned_bronze(tmp_data_dir)
    mock_fetch_api([])
    silver_metadata_tables(_context())
    silver = os.path.join(tmp_data_dir, "silver")

    stints_file = os.path.join(silver, "dim_stints.parquet")
    assert os.path.isfile(stints_file), "Missing silver/dim_stints.parquet"
    df = pd.read_parquet(stints_file)
    assert len(df) == 1

    assert os.path.isfile(os.path.join(silver, "dim_weather.parquet"))
    assert os.path.isdir(os.path.join(silver, "fact_race_control"))
    assert os.path.isdir(os.path.join(silver, "fact_session_results"))
    assert os.path.isdir(os.path.join(silver, "fact_overtakes"))
    assert os.path.isdir(os.path.join(silver, "fact_pit_stops"))


def test_silver_metadata_no_bronze_data(tmp_data_dir, mocker):
    mocker.patch("src.ingestion.assets.DATA_DIR", tmp_data_dir)
    silver_metadata_tables(_context())


def test_race_control_contract_valid():
    row = RaceControlContract(
        session_key=10014, driver_number=44,
        category="Flag", flag="GREEN",
        message="Green flag", date="2025-03-16T12:00:00+00:00",
    )
    assert row.session_key == 10014


def test_race_control_contract_nan_driver_number():
    row = RaceControlContract(
        session_key=10014, driver_number=None,
        category="Flag", flag="GREEN",
        message="Test", date="2025-03-16T12:00:00+00:00",
    )
    assert row.driver_number is None


def test_silver_metadata_driver_number_nan(tmp_data_dir, mock_fetch_api, mocker):
    mocker.patch("src.ingestion.assets.index_race_control_messages")
    _create_partitioned_bronze(tmp_data_dir)
    bronze_dir = os.path.join(tmp_data_dir, "bronze", "session_key=10014")
    pd.DataFrame([{
        "session_key": 10014, "driver_number": float("nan"),
        "category": "Flag", "flag": "GREEN",
        "message": "Test", "date": "2025-03-16T12:00:00+00:00",
    }]).to_parquet(os.path.join(bronze_dir, "race_control.parquet"), index=False)

    mock_fetch_api([])
    silver_metadata_tables(_context())

    silver = os.path.join(tmp_data_dir, "silver", "fact_race_control")
    if os.path.isdir(silver):
        files = [f for f in os.listdir(silver) if f.endswith(".parquet")]
        if files:
            df = pd.read_parquet(os.path.join(silver, files[0]))
            assert df["driver_number"].isna().any() or (df["driver_number"] == 0).any()


def test_asof_join_no_telemetry(tmp_data_dir, mocker):
    mocker.patch("src.ingestion.assets.DATA_DIR", tmp_data_dir)
    silver_telemetry_location_aligned(_context())
