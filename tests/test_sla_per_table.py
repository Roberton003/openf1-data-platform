import time

from src.web.routers.sla import GOLD_TABLES, _calc_table_freshness


def test_calc_freshness_file(tmp_path):
    test_file = tmp_path / "test.parquet"
    test_file.write_text("dummy")
    freshness = _calc_table_freshness(str(test_file))
    assert freshness is not None
    assert freshness > 0.0


def test_calc_freshness_directory(tmp_path):
    nested = tmp_path / "session_key=10014"
    nested.mkdir(parents=True)
    parquet = nested / "data.parquet"
    parquet.write_text("dummy")
    freshness = _calc_table_freshness(str(tmp_path))
    assert freshness is not None
    assert freshness > 0.0


def test_calc_freshness_no_file(tmp_path):
    freshness = _calc_table_freshness(str(tmp_path / "nonexistent.parquet"))
    assert freshness is None


def test_calc_freshness_empty_directory(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    freshness = _calc_table_freshness(str(empty_dir))
    assert freshness is None


def test_known_gold_tables():
    assert len(GOLD_TABLES) == 3
    assert "fct_f1_telemetry_analysis" in GOLD_TABLES
    assert "gold_features_lap_data" in GOLD_TABLES
    assert "gold_lap_predictions" in GOLD_TABLES


def test_freshness_decreases_over_time(tmp_path):
    test_file = tmp_path / "data.parquet"
    test_file.write_text("dummy")
    f1 = _calc_table_freshness(str(test_file))
    time.sleep(1)
    f2 = _calc_table_freshness(str(test_file))
    assert f2 > f1
