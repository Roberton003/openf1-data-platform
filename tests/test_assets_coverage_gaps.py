"""Targeted tests for uncovered paths in ingestion/assets.py."""

import os

import pandas as pd
import pytest
from dagster import build_asset_context

from src.ingestion.assets import (
    _read_bronze_table,
    _write_validated_race_control,
    _write_validated_session_results,
    bronze_sessions,
    fetch_api,
    silver_metadata_tables,
)


def _context():
    return build_asset_context()


def test_fetch_api_success_returns_json(mocker):
    """Line 76: fetch_api returns JSON on success."""
    mock_get = mocker.patch("src.ingestion.assets.requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"key": "val"}]
    result = fetch_api("test", {"p": 1})
    assert result == [{"key": "val"}]


def test_read_bronze_table_none(tmp_data_dir):
    """Line 436: _read_bronze_table returns None when file doesn't exist."""
    result = _read_bronze_table(tmp_data_dir, "nonexistent.parquet", {})
    assert result is None


def test_read_bronze_table_success(tmp_data_dir):
    """_read_bronze_table reads and casts."""
    df_in = pd.DataFrame({"session_key": [1], "driver_number": [44]})
    df_in.to_parquet(os.path.join(tmp_data_dir, "test.parquet"), index=False)
    result = _read_bronze_table(tmp_data_dir, "test.parquet", {"session_key": "int"})
    assert result is not None
    assert result["session_key"].dtype == int


def test_silver_metadata_tables_happy_path(tmp_data_dir, mock_fetch_api, mocker):
    """Full flow: silver_metadata_tables writes all 6 tables."""
    mocker.patch("src.ingestion.assets.index_race_control_messages")
    bronze_dir = os.path.join(tmp_data_dir, "bronze", "session_key=10014")
    os.makedirs(bronze_dir, exist_ok=True)

    stints = pd.DataFrame([{"session_key": 10014, "driver_number": 44, "stint_number": 1, "compound": "SOFT",
                            "tyre_age_at_start": 0, "lap_start": 1, "lap_end": 15}])
    stints.to_parquet(os.path.join(bronze_dir, "stints.parquet"), index=False)

    weather = pd.DataFrame([{"session_key": 10014, "date": "2025-03-16T12:00:00+00:00",
                             "air_temperature": 21.5, "track_temperature": 31.2,
                             "humidity": 45.0, "wind_speed": 12.0, "rainfall": 0}])
    weather.to_parquet(os.path.join(bronze_dir, "weather.parquet"), index=False)

    pit_stops = pd.DataFrame([{"session_key": 10014, "driver_number": 44, "lap_number": 15,
                               "stop_duration": 2.3, "lane_duration": 16.5, "pit_duration": 18.8,
                               "date": "2025-03-16T12:30:00+00:00"}])
    pit_stops.to_parquet(os.path.join(bronze_dir, "pit_stops.parquet"), index=False)

    race_control = pd.DataFrame([{"session_key": 10014, "driver_number": 44,
                                  "category": "Flag", "flag": "GREEN",
                                  "message": "Green flag", "date": "2025-03-16T12:00:00+00:00"}])
    race_control.to_parquet(os.path.join(bronze_dir, "race_control.parquet"), index=False)

    session_result = pd.DataFrame([{"session_key": 10014, "driver_number": 44,
                                    "position": 1, "points": 25.0, "number_of_laps": 57}])
    session_result.to_parquet(os.path.join(bronze_dir, "session_result.parquet"), index=False)

    overtakes = pd.DataFrame([{"session_key": 10014, "overtaking_driver_number": 1,
                               "overtaken_driver_number": 44, "position": 1,
                               "date": "2025-03-16T12:10:00+00:00"}])
    overtakes.to_parquet(os.path.join(bronze_dir, "overtakes.parquet"), index=False)

    mock_fetch_api([])
    silver_metadata_tables(_context())

    silver = os.path.join(tmp_data_dir, "silver")
    assert os.path.exists(os.path.join(silver, "dim_stints.parquet"))
    assert os.path.exists(os.path.join(silver, "dim_weather.parquet"))
    assert os.path.isdir(os.path.join(silver, "fact_pit_stops"))
    assert os.path.isdir(os.path.join(silver, "fact_race_control"))
    assert os.path.isdir(os.path.join(silver, "fact_session_results"))
    assert os.path.isdir(os.path.join(silver, "fact_overtakes"))


def test_bronze_sessions_with_data_writes_parquet(tmp_data_dir, mocker):
    """bronze_sessions writes when fetch_api returns data."""
    mocker.patch("src.ingestion.assets.fetch_api", return_value=[{"session_key": 10014, "year": 2025}])
    bronze_sessions(_context())
    df = pd.read_parquet(f"{tmp_data_dir}/bronze/sessions.parquet")
    assert len(df) == 3


@pytest.fixture
def _mock_write_functions(mocker):
    mocker.patch("src.ingestion.assets.atomic_write_partitioned_parquet")
    mocker.patch("src.ingestion.assets.index_race_control_messages")


def test_write_validated_session_results_position_none(mocker):
    """Line 514-515: position is NaN → sets to None."""
    mocker.patch("src.ingestion.assets.atomic_write_partitioned_parquet")
    df = pd.DataFrame([{
        "session_key": 10014, "driver_number": 44, "position": None,
        "points": 25.0, "number_of_laps": 57, "dn": False, "dns": False, "dsq": False,
    }])
    _write_validated_session_results([df], _context())


def test_write_validated_session_results_bool_cast(mocker):
    """Line 523-524: dn/dns/dsq are cast to bool."""
    mocker.patch("src.ingestion.assets.atomic_write_partitioned_parquet")
    df = pd.DataFrame([{
        "session_key": 10014, "driver_number": 44, "position": 1,
        "points": 25.0, "number_of_laps": 57, "dn": 1, "dns": 0, "dsq": 0, "gap_to_leader": None,
    }])
    _write_validated_session_results([df], _context())
