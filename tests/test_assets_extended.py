"""Tests for ingestion/assets.py — additional functions for coverage."""

import os

import pandas as pd

from src.ingestion.assets import (
    SESSIONS_TO_PROCESS,
    IngestionConfig,
    _append_execution_record,
    _calc_freshness_minutes,
    _write_session_partition,
)


def test_sessions_to_process_has_bahrain():
    gps = [s["gp"] for s in SESSIONS_TO_PROCESS]
    assert "Bahrain" in gps


def test_sessions_to_process_has_keys():
    for s in SESSIONS_TO_PROCESS:
        assert "year" in s
        assert "session_key" in s
        assert "gp" in s


def test_write_session_partition(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    _write_session_partition(df, str(tmp_path))
    assert (tmp_path / "data.parquet").exists()
    result = pd.read_parquet(tmp_path / "data.parquet")
    assert len(result) == 2


def test_append_execution_record(tmp_path):
    record = {"run_id": 1, "status": "success"}
    _append_execution_record(str(tmp_path), record)
    assert (tmp_path / "data.parquet").exists()
    result = pd.read_parquet(tmp_path / "data.parquet")
    assert len(result) == 1
    assert result.iloc[0]["run_id"] == 1


def test_append_execution_record_merges(tmp_path):
    _append_execution_record(str(tmp_path), {"run_id": 1})
    _append_execution_record(str(tmp_path), {"run_id": 2})
    result = pd.read_parquet(tmp_path / "data.parquet")
    assert len(result) == 2


def test_ingestion_config_default():
    config = IngestionConfig()
    assert config is not None


def test_calc_freshness_minutes_with_data(tmp_path):
    (tmp_path / "test.txt").write_text("data")
    result = _calc_freshness_minutes(str(tmp_path))
    assert result is not None
    assert result >= 0.0


def test_calc_freshness_minutes_none():
    assert _calc_freshness_minutes(None) is None


def test_calc_freshness_minutes_nonexistent():
    assert _calc_freshness_minutes("/nonexistent/path") is None


def test_calc_freshness_minutes_empty(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _calc_freshness_minutes(str(empty)) is None
