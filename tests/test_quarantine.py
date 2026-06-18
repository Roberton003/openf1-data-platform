import os

import pandas as pd

from src.ingestion.process import quarantine_invalid_rows


def test_quarantine_creates_file(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    quarantine_invalid_rows(df, "test_table", "validation_error", str(tmp_path))
    files = os.listdir(tmp_path)
    assert any("test_table" in f for f in files)


def test_quarantine_adds_metadata_columns(tmp_path):
    df = pd.DataFrame({"a": [1]})
    quarantine_invalid_rows(df, "test_table", "bad_data", str(tmp_path))
    parquet_files = [f for f in os.listdir(tmp_path) if f.endswith(".parquet")]
    assert len(parquet_files) == 1
    result = pd.read_parquet(os.path.join(tmp_path, parquet_files[0]))
    assert "quarantine_timestamp" in result.columns
    assert "quarantine_reason" in result.columns
    assert (result["quarantine_reason"] == "bad_data").all()


def test_quarantine_empty_dataframe_does_nothing(tmp_path):
    df = pd.DataFrame()
    quarantine_invalid_rows(df, "test_table", "empty", str(tmp_path))
    files = os.listdir(tmp_path)
    parquet_files = [f for f in files if f.endswith(".parquet")]
    assert len(parquet_files) == 0


def test_quarantine_preserves_original_columns(tmp_path):
    df = pd.DataFrame({"session_key": [10014], "driver_number": [44], "speed": [312]})
    quarantine_invalid_rows(df, "car_data", "speed_out_of_range", str(tmp_path))
    parquet_files = [f for f in os.listdir(tmp_path) if f.endswith(".parquet")]
    result = pd.read_parquet(os.path.join(tmp_path, parquet_files[0]))
    assert "session_key" in result.columns
    assert "driver_number" in result.columns
    assert "speed" in result.columns
    assert len(result) == 1


def test_quarantine_multiple_tables(tmp_path):
    df1 = pd.DataFrame({"id": [1]})
    df2 = pd.DataFrame({"id": [2]})
    quarantine_invalid_rows(df1, "table_a", "error_a", str(tmp_path))
    quarantine_invalid_rows(df2, "table_b", "error_b", str(tmp_path))
    files = os.listdir(tmp_path)
    assert any("table_a" in f for f in files)
    assert any("table_b" in f for f in files)
