"""Tests for ingestion/assets.py — Bronze layer assets (bronze_sessions, bronze_drivers)."""

import os

import pandas as pd
import pytest
from dagster import build_asset_context

from src.ingestion.assets import bronze_sessions, bronze_drivers


def _context():
    return build_asset_context()


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


def test_bronze_drivers_no_sessions_file(tmp_data_dir, mocker):
    mocker.patch("src.ingestion.assets.fetch_api", return_value=[])
    bronze_drivers(_context())
    assert not os.path.exists(f"{tmp_data_dir}/bronze/drivers.parquet")
