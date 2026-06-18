"""Tests for ingestion/assets.py — freshness calculation and utility functions."""

import time

from src.ingestion.assets import _calc_freshness_minutes


def test_calc_freshness_returns_minutes(tmp_path):
    test_file = tmp_path / "data.parquet"
    test_file.write_text("dummy")
    freshness = _calc_freshness_minutes(str(tmp_path))
    assert freshness is not None
    assert freshness >= 0.0


def test_calc_freshness_none_for_nonexistent():
    result = _calc_freshness_minutes("/nonexistent/path/that/does/not/exist")
    assert result is None


def test_calc_freshness_none_for_none():
    result = _calc_freshness_minutes(None)
    assert result is None


def test_calc_freshness_none_for_empty_dir(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = _calc_freshness_minutes(str(empty_dir))
    assert result is None


def test_calc_freshness_increases_over_time(tmp_path):
    test_file = tmp_path / "data.parquet"
    test_file.write_text("dummy")
    f1 = _calc_freshness_minutes(str(tmp_path))
    time.sleep(1)
    f2 = _calc_freshness_minutes(str(tmp_path))
    assert f2 >= f1


def test_calc_freshness_nested_dirs(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("content")
    freshness = _calc_freshness_minutes(str(tmp_path))
    assert freshness is not None


def test_calc_freshness_skips_directories(tmp_path):
    (tmp_path / "subdir").mkdir()
    result = _calc_freshness_minutes(str(tmp_path))
    assert result is None


def test_calc_freshness_file_only(tmp_path):
    test_file = tmp_path / "single.parquet"
    test_file.write_text("data")
    freshness = _calc_freshness_minutes(str(tmp_path))
    assert freshness is not None
    assert freshness >= 0.0
