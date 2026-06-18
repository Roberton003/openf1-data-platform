"""Tests for ingestion/storage.py — atomic write functions."""

import os

import pandas as pd

from src.ingestion.storage import (
    atomic_append_partitioned_file,
    atomic_write_dataframe,
    atomic_write_partitioned_parquet,
)


def test_atomic_write_dataframe_creates_file(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    target = str(tmp_path / "test.parquet")
    atomic_write_dataframe(df, target)
    assert os.path.exists(target)
    result = pd.read_parquet(target)
    assert len(result) == 2


def test_atomic_write_dataframe_replaces_existing(tmp_path):
    df1 = pd.DataFrame({"a": [1]})
    df2 = pd.DataFrame({"a": [1, 2, 3]})
    target = str(tmp_path / "test.parquet")
    atomic_write_dataframe(df1, target)
    atomic_write_dataframe(df2, target)
    result = pd.read_parquet(target)
    assert len(result) == 3


def test_atomic_write_partitioned_parquet(tmp_path):
    df = pd.DataFrame({"session_key": [1, 1, 2], "val": [10, 20, 30]})
    target = str(tmp_path / "partitioned")
    atomic_write_partitioned_parquet(df, target, ["session_key"])
    assert os.path.exists(target)
    result = pd.read_parquet(target)
    assert len(result) == 3


def test_atomic_append_creates_new_file(tmp_path):
    df = pd.DataFrame({"a": [1]})
    target = str(tmp_path / "append_test.parquet")
    atomic_append_partitioned_file(target, df)
    result = pd.read_parquet(target)
    assert len(result) == 1


def test_atomic_append_merges_existing(tmp_path):
    df1 = pd.DataFrame({"a": [1]})
    df2 = pd.DataFrame({"a": [2]})
    target = str(tmp_path / "append_test.parquet")
    atomic_append_partitioned_file(target, df1)
    atomic_append_partitioned_file(target, df2)
    result = pd.read_parquet(target)
    assert len(result) == 2
