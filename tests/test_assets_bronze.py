"""Tests for ingestion/assets.py — Bronze layer assets."""

import logging
import os

import pandas as pd
import pytest
from dagster import build_asset_context

from src.ingestion.assets import (
    bronze_drivers,
    bronze_race_control_and_stints,
    bronze_sessions,
    bronze_telemetry_spatial,
)


def _context():
    return build_asset_context()


# --- bronze_sessions ---


def test_bronze_sessions_writes_parquet(tmp_data_dir, mock_fetch_api):
    """bronze_sessions loops over 3 SESSIONS_TO_PROCESS; mock returns same data each time."""
    mock_fetch_api([{"session_key": 10014, "year": 2025, "session_name": "Race"}])
    bronze_sessions(_context())
    df = pd.read_parquet(f"{tmp_data_dir}/bronze/sessions.parquet")
    assert len(df) == 3
    assert df.iloc[0]["session_key"] == 10014


def test_bronze_sessions_empty_data_skips_write(tmp_data_dir, mock_fetch_api):
    mock_fetch_api([])
    bronze_sessions(_context())
    assert not os.path.exists(f"{tmp_data_dir}/bronze/sessions.parquet")


def test_bronze_sessions_404_skips_gracefully(tmp_data_dir, mocker):
    mocker.patch("src.ingestion.assets.fetch_api", return_value=[])
    bronze_sessions(_context())
    assert not os.path.exists(f"{tmp_data_dir}/bronze/sessions.parquet")


# --- bronze_drivers ---


def test_bronze_drivers_no_sessions_file(tmp_data_dir, mocker):
    mocker.patch("src.ingestion.assets.fetch_api", return_value=[])
    bronze_drivers(_context())
    assert not os.path.exists(f"{tmp_data_dir}/bronze/drivers.parquet")


# --- bronze_race_control_and_stints ---


def test_bronze_rc_stints_writes_all_tables(tmp_data_dir, mock_fetch_api):
    """Writes parquet for all 6 endpoints × 3 sessions = 18 files."""
    mock_fetch_api([{"session_key": 10014, "gap_to_leader": "0.5", "interval": "1.2"}])
    bronze_race_control_and_stints(_context())
    skey = 10014
    part = f"session_key={skey}"
    base = f"{tmp_data_dir}/bronze/{part}"
    for name in ("stints", "pit_stops", "race_control", "weather", "session_result", "overtakes"):
        assert os.path.exists(f"{base}/{name}.parquet"), f"Missing {name}.parquet"


def test_bronze_rc_stints_empty_api_skips_write(tmp_data_dir, mock_fetch_api):
    mock_fetch_api([])
    bronze_race_control_and_stints(_context())
    bronze_dir = f"{tmp_data_dir}/bronze/"
    assert not os.path.isdir(bronze_dir) or not os.listdir(bronze_dir)


def test_bronze_rc_stints_partial_data(tmp_data_dir, mock_fetch_api):
    """Only stints + weather return data — only those files should exist."""
    def side_effect(endpoint, _params):
        return [{"session_key": 10014}] if endpoint in ("stints", "weather") else []
    m = mock_fetch_api()
    m.side_effect = side_effect
    bronze_race_control_and_stints(_context())
    part = f"{tmp_data_dir}/bronze/session_key=10014"
    assert os.path.exists(f"{part}/stints.parquet")
    assert os.path.exists(f"{part}/weather.parquet")
    assert not os.path.exists(f"{part}/pit_stops.parquet")
    assert not os.path.exists(f"{part}/race_control.parquet")


# --- bronze_telemetry_spatial ---


def _create_sample_drivers_parquet(path: str):
    """Helper: create drivers.parquet with two focus drivers for session 10014."""
    p = os.path.join(path, "bronze")
    os.makedirs(p, exist_ok=True)
    pd.DataFrame([
        {"session_key": 10014, "driver_number": 1, "full_name": "Driver A", "name_acronym": "DA",
         "team_name": "Team A", "country_code": "BR"},
        {"session_key": 10014, "driver_number": 16, "full_name": "Driver B", "name_acronym": "DB",
         "team_name": "Team B", "country_code": "GB"},
        {"session_key": 10014, "driver_number": 44, "full_name": "Driver C", "name_acronym": "DC",
         "team_name": "Team C", "country_code": "NL"},
    ]).to_parquet(os.path.join(p, "drivers.parquet"), index=False)


def test_bronze_telemetry_writes_driver_files(tmp_data_dir, mock_fetch_api):
    """Writes car_data, location, intervals for each active focus driver."""
    _create_sample_drivers_parquet(tmp_data_dir)
    mock_fetch_api([{"driver_number": 1, "x": "100", "y": "200", "z": "5",
                     "gap_to_leader": "0.5", "interval": "1.2"}])
    bronze_telemetry_spatial(_context())
    part = f"{tmp_data_dir}/bronze/session_key=10014"
    assert os.path.exists(f"{part}/car_data_1.parquet")
    assert os.path.exists(f"{part}/location_1.parquet")
    assert os.path.exists(f"{part}/intervals_1.parquet")


def test_bronze_telemetry_no_drivers_file(tmp_data_dir, mock_fetch_api, capsys):
    """Missing drivers.parquet → early return with warning."""
    mock_fetch_api([])
    bronze_telemetry_spatial(_context())
    captured = capsys.readouterr()
    assert "pilotos brutos ausente" in captured.err


def test_bronze_telemetry_partial_data(tmp_data_dir, mock_fetch_api):
    """Only telemetry endpoint returns data; location and intervals are empty."""
    _create_sample_drivers_parquet(tmp_data_dir)
    def side_effect(endpoint, _params):
        return [{"driver_number": 1}] if endpoint == "car_data" else []
    m = mock_fetch_api()
    m.side_effect = side_effect
    bronze_telemetry_spatial(_context())
    part = f"{tmp_data_dir}/bronze/session_key=10014"
    assert os.path.exists(f"{part}/car_data_1.parquet")
    assert not os.path.exists(f"{part}/location_1.parquet")


def test_bronze_telemetry_location_coords_casted(tmp_data_dir, mock_fetch_api):
    """Coordinates x/y/z are cast to int via pd.to_numeric."""
    _create_sample_drivers_parquet(tmp_data_dir)
    mock_fetch_api([{"driver_number": 1, "x": "100.7", "y": "200.3", "z": None}])
    bronze_telemetry_spatial(_context())
    df = pd.read_parquet(f"{tmp_data_dir}/bronze/session_key=10014/location_1.parquet")
    assert df["x"].iloc[0] == 100
    assert df["y"].iloc[0] == 200
    assert df["z"].iloc[0] == 0
