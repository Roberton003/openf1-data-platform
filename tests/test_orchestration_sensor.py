"""Tests for Dagster orchestration — sensor."""

from dagster import DagsterInstance, build_sensor_context

from src.orchestration.sensors import freshness_sensor


def test_sensor_name():
    assert freshness_sensor.name == "freshness_sensor"


def test_sensor_min_interval():
    assert freshness_sensor.minimum_interval_seconds == 3600


def test_sensor_returns_nothing_when_bronze_fresh(tmp_path):
    bronze = tmp_path / "bronze" / "2025" / "Race"
    bronze.mkdir(parents=True)
    (bronze / "data.parquet").write_text("dummy")
    import os
    from src.orchestration.sensors import DATA_DIR
    original = DATA_DIR
    import src.orchestration.sensors as sensors
    sensors.DATA_DIR = str(tmp_path)
    try:
        context = build_sensor_context(instance=DagsterInstance.ephemeral())
        result = list(freshness_sensor(context))
        assert len(result) == 0
    finally:
        sensors.DATA_DIR = original


def test_sensor_triggers_when_bronze_missing(tmp_path):
    from src.orchestration.sensors import DATA_DIR
    import src.orchestration.sensors as sensors
    sensors.DATA_DIR = str(tmp_path)
    try:
        context = build_sensor_context(instance=DagsterInstance.ephemeral())
        result = list(freshness_sensor(context))
        assert len(result) == 1
        run_request = result[0]
        assert run_request.tags["trigger"] == "missing_bronze"
    finally:
        sensors.DATA_DIR = DATA_DIR


def test_sensor_triggers_when_bronze_stale(tmp_path):
    import os
    import time
    bronze = tmp_path / "bronze" / "2025"
    bronze.mkdir(parents=True)
    old_file = bronze / "old.parquet"
    old_file.write_text("dummy")
    old_mtime = time.time() - 25 * 3600
    os.utime(str(old_file), (old_mtime, old_mtime))
    from src.orchestration.sensors import DATA_DIR
    import src.orchestration.sensors as sensors
    sensors.DATA_DIR = str(tmp_path)
    try:
        context = build_sensor_context(instance=DagsterInstance.ephemeral())
        result = list(freshness_sensor(context))
        assert len(result) == 1
        run_request = result[0]
        assert run_request.tags["trigger"] == "stale_data"
    finally:
        sensors.DATA_DIR = DATA_DIR


def test_sensor_returns_nothing_when_empty_bronze(tmp_path):
    bronze = tmp_path / "bronze"
    bronze.mkdir(parents=True)
    from src.orchestration.sensors import DATA_DIR
    import src.orchestration.sensors as sensors
    sensors.DATA_DIR = str(tmp_path)
    try:
        context = build_sensor_context(instance=DagsterInstance.ephemeral())
        result = list(freshness_sensor(context))
        assert len(result) == 0
    finally:
        sensors.DATA_DIR = DATA_DIR


def test_sensor_registered_in_defs():
    from src.orchestration.definitions import defs
    names = [s.name for s in defs.sensors]
    assert "freshness_sensor" in names
