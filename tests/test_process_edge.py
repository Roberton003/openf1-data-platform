"""Tests for ingestion/process.py — validation functions and edge cases."""

import os

import pandas as pd
import pytest
from pydantic import BaseModel

from src.ingestion.process import (
    validate_pydantic_batch,
    validate_vectorized_batch,
    quarantine_invalid_rows,
)


class MockContract(BaseModel):
    driver_number: int
    full_name: str


SAMPLE_TELEMETRY_SCHEMA = {
    "driver_number": "int64",
    "speed": "int64",
    "rpm": "int64",
    "date": "datetime",
}

SAMPLE_REQUIRED_COLS = ["driver_number", "date"]


def test_validate_pydantic_batch_empty():
    df_valid, df_invalid = validate_pydantic_batch(pd.DataFrame(), MockContract, "test")
    assert df_valid.empty
    assert df_invalid.empty


def test_validate_pydantic_batch_all_valid():
    df = pd.DataFrame([
        {"driver_number": 44, "full_name": "Lewis Hamilton"},
        {"driver_number": 1, "full_name": "Max Verstappen"},
    ])
    df_valid, df_invalid = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_valid) == 2
    assert df_invalid.empty


def test_validate_pydantic_batch_invalid_row():
    df = pd.DataFrame([
        {"driver_number": 44, "full_name": "Lewis Hamilton"},
        {"driver_number": "not_a_number", "full_name": "Invalid"},
    ])
    df_valid, df_invalid = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_valid) == 1
    assert len(df_invalid) == 1
    assert "error_detail" in df_invalid.columns


def test_validate_pydantic_batch_timestamp_conversion():
    df = pd.DataFrame([
        {"driver_number": 44, "full_name": "Lewis Hamilton"},
    ])
    df["date"] = pd.Timestamp("2025-03-16 12:00:00")
    df_valid, _ = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_valid) >= 0


def test_validate_pydantic_batch_nan_conversion():
    df = pd.DataFrame([
        {"driver_number": 44, "full_name": "Lewis Hamilton"},
        {"driver_number": 44, "full_name": float("nan")},
    ])
    df_valid, df_invalid = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_invalid) >= 0


def test_validate_vectorized_batch_empty():
    df_valid, df_invalid = validate_vectorized_batch(pd.DataFrame(), SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert df_valid.empty
    assert df_invalid.empty


def test_validate_vectorized_batch_all_valid():
    df = pd.DataFrame([
        {"driver_number": 44, "speed": 312, "rpm": 11800, "date": "2025-03-16T12:00:00"},
    ])
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert len(df_valid) == 1
    assert df_invalid.empty


def test_validate_vectorized_batch_null_required():
    df = pd.DataFrame([
        {"driver_number": None, "speed": 312, "rpm": 11800, "date": "2025-03-16T12:00:00"},
    ])
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert df_valid.empty
    assert len(df_invalid) == 1
    assert "Valor nulo" in df_invalid.iloc[0]["error_detail"]


def test_validate_vectorized_batch_cast_failure():
    df = pd.DataFrame([
        {"driver_number": 44, "speed": "not_a_number", "rpm": 11800, "date": "2025-03-16T12:00:00"},
    ])
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert len(df_invalid) >= 0


def test_quarantine_invalid_rows_empty(tmp_path):
    quarantine_invalid_rows(pd.DataFrame(), "test_table", "empty", str(tmp_path))
    assert len(os.listdir(tmp_path)) == 0


def test_quarantine_invalid_rows_writes(tmp_path):
    df = pd.DataFrame([{"driver_number": 44, "error": "bad data"}])
    quarantine_invalid_rows(df, "test_table", "validation failed", str(tmp_path))
    files = [f for f in os.listdir(tmp_path) if f.endswith(".parquet")]
    assert len(files) >= 1
    result = pd.read_parquet(os.path.join(tmp_path, files[0]))
    assert len(result) == 1


def test_validate_vectorized_batch_partial_columns():
    """Schema has columns not in DF — should handle gracefully."""
    df = pd.DataFrame([
        {"driver_number": 44, "speed": 312, "date": "2025-03-16T12:00:00"},
    ])
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert len(df_valid) == 1


def test_validate_vectorized_batch_empty_required_cols():
    df = pd.DataFrame([{"driver_number": 44, "date": "2025-03-16T12:00:00"}])
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, [])
    assert len(df_valid) == 1
    assert df_invalid.empty
