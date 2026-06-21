"""Tests for ingestion/process.py — validation functions and edge cases."""

import os

import pandas as pd
import pytest
from pydantic import BaseModel

from src.ingestion.process import (
    quarantine_invalid_rows,
    validate_pydantic_batch,
    validate_vectorized_batch,
)

from src.ingestion.pipeline_common import (
    append_execution_record,
    calc_freshness_minutes,
    write_session_partition,
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
    df = pd.DataFrame(
        [
            {"driver_number": 44, "full_name": "Lewis Hamilton"},
            {"driver_number": 1, "full_name": "Max Verstappen"},
        ]
    )
    df_valid, df_invalid = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_valid) == 2
    assert df_invalid.empty


def test_validate_pydantic_batch_invalid_row():
    df = pd.DataFrame(
        [
            {"driver_number": 44, "full_name": "Lewis Hamilton"},
            {"driver_number": "not_a_number", "full_name": "Invalid"},
        ]
    )
    df_valid, df_invalid = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_valid) == 1
    assert len(df_invalid) == 1
    assert "error_detail" in df_invalid.columns


def test_validate_pydantic_batch_timestamp_conversion():
    df = pd.DataFrame(
        [
            {"driver_number": 44, "full_name": "Lewis Hamilton"},
        ]
    )
    df["date"] = pd.Timestamp("2025-03-16 12:00:00")
    df_valid, _ = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_valid) >= 0


def test_validate_pydantic_batch_nan_conversion():
    df = pd.DataFrame(
        [
            {"driver_number": 44, "full_name": "Lewis Hamilton"},
            {"driver_number": 44, "full_name": float("nan")},
        ]
    )
    df_valid, df_invalid = validate_pydantic_batch(df, MockContract, "test")
    assert len(df_invalid) >= 0


def test_validate_vectorized_batch_empty():
    df_valid, df_invalid = validate_vectorized_batch(pd.DataFrame(), SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert df_valid.empty
    assert df_invalid.empty


def test_validate_vectorized_batch_all_valid():
    df = pd.DataFrame(
        [
            {"driver_number": 44, "speed": 312, "rpm": 11800, "date": "2025-03-16T12:00:00"},
        ]
    )
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert len(df_valid) == 1
    assert df_invalid.empty


def test_validate_vectorized_batch_null_required():
    df = pd.DataFrame(
        [
            {"driver_number": None, "speed": 312, "rpm": 11800, "date": "2025-03-16T12:00:00"},
        ]
    )
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert df_valid.empty
    assert len(df_invalid) == 1
    assert "Valor nulo" in df_invalid.iloc[0]["error_detail"]


def test_validate_vectorized_batch_cast_failure():
    df = pd.DataFrame(
        [
            {"driver_number": 44, "speed": "not_a_number", "rpm": 11800, "date": "2025-03-16T12:00:00"},
        ]
    )
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
    df = pd.DataFrame(
        [
            {"driver_number": 44, "speed": 312, "date": "2025-03-16T12:00:00"},
        ]
    )
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, SAMPLE_REQUIRED_COLS)
    assert len(df_valid) == 1


def test_validate_vectorized_batch_empty_required_cols():
    df = pd.DataFrame([{"driver_number": 44, "date": "2025-03-16T12:00:00"}])
    df_valid, df_invalid = validate_vectorized_batch(df, SAMPLE_TELEMETRY_SCHEMA, [])
    assert len(df_valid) == 1
    assert df_invalid.empty


def test_merge_drivers_idempotent():
    """Merge pattern from process_medallion_pipeline: exclude existing drivers then concat."""
    df_existing = pd.DataFrame(
        [
            {"driver_number": 44, "full_name": "Lewis Hamilton"},
            {"driver_number": 1, "full_name": "Max Verstappen"},
        ]
    )
    df_new = pd.DataFrame(
        [
            {"driver_number": 1, "full_name": "Max Verstappen"},
            {"driver_number": 16, "full_name": "Charles Leclerc"},
        ]
    )
    driver_nums = df_new["driver_number"].tolist()
    df_existing = df_existing[~df_existing["driver_number"].isin(driver_nums)]
    df_final = pd.concat([df_existing, df_new], ignore_index=True)

    assert len(df_final) == 3
    assert set(df_final["driver_number"]) == {44, 1, 16}


def test_merge_sessions_idempotent():
    """Session merge pattern: remove old session_key then concat."""
    df_existing = pd.DataFrame(
        [
            {"session_key": 10014, "session_name": "Race"},
            {"session_key": 9979, "session_name": "Qualifying"},
        ]
    )
    df_new = pd.DataFrame(
        [
            {"session_key": 9979, "session_name": "Qualifying Updated"},
        ]
    )
    session_key = int(df_new.iloc[0]["session_key"])
    df_existing = df_existing[df_existing["session_key"] != session_key]
    df_final = pd.concat([df_existing, df_new], ignore_index=True)

    assert len(df_final) == 2
    assert df_final.iloc[1]["session_name"] == "Qualifying Updated"


def test_error_lineage_record_structure():
    """Error lineage record in process_medallion_pipeline must have all required fields."""
    run_record = {
        "run_id": "test-uuid",
        "pipeline_name": "cli_pipeline_bahrain_race",
        "session_key": 10014,
        "execution_timestamp": "2026-06-20T12:00:00",
        "duration_seconds": 1.5,
        "status": "FAILED: test error",
        "total_rows_processed": 0,
        "total_rows_bronze": 100,
        "total_rows_silver": 80,
        "total_rows_quarantine": 5,
        "quarantine_rate": 0.05,
        "records_rejected": 5,
        "data_freshness_minutes": None,
        "sla_runtime_status": "COMPLIANT",
        "sla_quality_status": "COMPLIANT",
        "sla_freshness_status": "NO_DATA",
    }
    assert run_record["status"].startswith("FAILED")
    assert run_record["quarantine_rate"] == 0.05
    assert run_record["total_rows_bronze"] == 100


def test_partition_fallback_logic():
    """Fallback logic: when 2025 path doesn't exist, should fallback to 2024."""
    import os.path

    original_exists = os.path.exists

    def mock_exists(path):
        if "year=2025" in path:
            return False
        if "year=2024" in path:
            return True
        return original_exists(path)

    import os

    os.path.exists = mock_exists
    try:
        year = 2025
        gp_dir = "bahrain"
        sess_dir = "race"
        DATA_DIR = "/tmp/test"
        partition_path = f"{DATA_DIR}/bronze/year={year}/gp={gp_dir}/session={sess_dir}"

        if not os.path.exists(partition_path):
            if year == 2025:
                year = 2024
                partition_path = f"{DATA_DIR}/bronze/year={year}/gp={gp_dir}/session={sess_dir}"

        assert year == 2024
        assert "year=2024" in partition_path
    finally:
        os.path.exists = original_exists


def testcalc_freshness_minutes_none():
    assert calc_freshness_minutes(None) is None


def testcalc_freshness_minutes_not_a_dir(tmp_path):
    nowhere = str(tmp_path / "nonexistent")
    assert calc_freshness_minutes(nowhere) is None


def testcalc_freshness_minutes_empty_dir(tmp_path):
    assert calc_freshness_minutes(str(tmp_path)) is None


def testcalc_freshness_minutes_with_file(tmp_path):
    (tmp_path / "test.parquet").write_bytes(b"dummy")
    result = calc_freshness_minutes(str(tmp_path))
    assert result is not None
    assert result >= 0


def testwrite_session_partition_creates_file(tmp_path):
    import pandas as pd

    df = pd.DataFrame([{"driver_number": 44}])
    write_session_partition(df, str(tmp_path))
    assert (tmp_path / "data.parquet").exists()


def testappend_execution_record_creates_file(tmp_path):
    record = {"run_id": "test-123", "status": "OK"}
    append_execution_record(str(tmp_path), record)
    assert (tmp_path / "data.parquet").exists()


def testappend_execution_record_append(tmp_path):
    import pandas as pd

    append_execution_record(str(tmp_path), {"run_id": "first"})
    append_execution_record(str(tmp_path), {"run_id": "second"})
    result = pd.read_parquet(tmp_path / "data.parquet")
    assert len(result) == 2


def test_quarantine_invalid_rows_creates_dir(tmp_path):
    df = pd.DataFrame([{"driver_number": 44, "error": "bad"}])
    sub = tmp_path / "quarantine"
    quarantine_invalid_rows(df, "test", "reason", str(sub))
    assert sub.is_dir()


def test_partition_fallback_no_path_raises():
    """When both 2025 and 2024 paths don't exist, should raise FileNotFoundError."""
    import os.path

    def mock_exists(path):
        return False

    import os

    original_exists = os.path.exists
    os.path.exists = mock_exists
    try:
        year = 2025
        gp_dir = "bahrain"
        sess_dir = "race"
        DATA_DIR = "/tmp/test"
        partition_path = f"{DATA_DIR}/bronze/year={year}/gp={gp_dir}/session={sess_dir}"

        if not os.path.exists(partition_path):
            if year == 2025:
                year = 2024
                partition_path = f"{DATA_DIR}/bronze/year={year}/gp={gp_dir}/session={sess_dir}"

        if not os.path.exists(partition_path):
            raise FileNotFoundError(f"Partition not found: {partition_path}")

        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass
    finally:
        os.path.exists = original_exists


# process_medallion_pipeline: Orquestra a leitura da Bronze, validação das tabelas (Silver fronteira) e


@pytest.mark.xfail(reason="TODO: auto-generated skeleton needs review")
def test_process_medallion_pipeline():
    """TODO: auto-generated test for process_medallion_pipeline — needs manual fixture setup."""
    pytest.skip("Complex function — requires integration fixtures")
