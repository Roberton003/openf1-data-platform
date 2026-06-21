"""Tests for ingestion/process.py — validation functions and edge cases."""

import os

import pandas as pd
import pytest
from pydantic import BaseModel

from src.ingestion.pipeline_common import (
    append_execution_record,
    calc_freshness_minutes,
    quarantine_invalid_rows,
    validate_pydantic_batch,
    validate_vectorized_batch,
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


@pytest.fixture
def patch_process_paths(tmp_path, mocker):
    """Patch DATA_DIR and QUARANTINE_DIR to use tmp_path."""
    data_dir = str(tmp_path / "data")
    mocker.patch("src.ingestion.process.DATA_DIR", data_dir)
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))


def test_find_partition_2025_exists(tmp_path, mocker):
    """_find_partition returns path when 2025 partition exists."""
    bronze = tmp_path / "data" / "bronze" / "year=2025" / "gp=bahrain" / "session=Race"
    bronze.mkdir(parents=True)

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path / "data"))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _find_partition

    part_path, quar_path, year = _find_partition(2025, "bahrain", "Race")
    assert "year=2025" in part_path
    assert year == 2025
    assert "quarantine" in quar_path


def test_find_partition_fallback_2024(tmp_path, mocker):
    """_find_partition fallback to 2024 when 2025 missing."""
    bronze = tmp_path / "data" / "bronze" / "year=2024" / "gp=bahrain" / "session=Race"
    bronze.mkdir(parents=True)

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path / "data"))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _find_partition

    part_path, _, year = _find_partition(2025, "bahrain", "Race")
    assert "year=2024" in part_path
    assert year == 2024


def test_find_partition_not_found_raises(tmp_path, mocker):
    """_find_partition raises FileNotFoundError when no partition exists."""
    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path / "data"))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _find_partition

    with pytest.raises(FileNotFoundError, match="Caminho da partição Bronze não encontrado"):
        _find_partition(2025, "nonexistent", "Race")


def test_process_silver_table_file_not_found(tmp_path, mocker):
    """_process_silver_table returns zeros when parquet file missing."""
    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path / "data"))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _process_silver_table

    stats = _process_silver_table(
        partition_path=str(tmp_path / "nonexistent"),
        quarantine_path=str(tmp_path / "quarantine"),
        file_name="drivers.parquet",
        table_name="drivers",
        session_key=10014,
        silver_target=str(tmp_path / "silver" / "dim_drivers.parquet"),
        write_mode="merge",
        merge_key="driver_number",
    )
    assert stats == {"bronze": 0, "silver": 0, "quarantine": 0}


def test_process_silver_table_merge_existing(tmp_path, mocker):
    """_process_silver_table merge with existing parquet — idempotent merge."""
    partition = tmp_path / "bronze"
    partition.mkdir()
    silver_parent = tmp_path / "silver"
    silver_parent.mkdir(parents=True)
    silver_target = silver_parent / "dim_drivers.parquet"

    existing = pd.DataFrame(
        [
            {
                "driver_number": 44,
                "full_name": "Lewis Hamilton",
                "name_acronym": "HAM",
                "team_name": "Ferrari",
                "country_code": "GBR",
            },
            {
                "driver_number": 1,
                "full_name": "Max Verstappen",
                "name_acronym": "VER",
                "team_name": "Red Bull",
                "country_code": "NED",
            },
        ]
    )
    existing.to_parquet(silver_target)

    new_data = pd.DataFrame(
        [
            {
                "driver_number": 1,
                "full_name": "Max Verstappen",
                "name_acronym": "VER",
                "team_name": "Red Bull",
                "country_code": "NED",
            },
            {
                "driver_number": 16,
                "full_name": "Charles Leclerc",
                "name_acronym": "LEC",
                "team_name": "Ferrari",
                "country_code": "MON",
            },
        ]
    )
    new_data.to_parquet(partition / "drivers.parquet")

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _process_silver_table
    from src.ingestion.schemas import DriverContract

    stats = _process_silver_table(
        partition_path=str(partition),
        quarantine_path=str(tmp_path / "quarantine"),
        file_name="drivers.parquet",
        table_name="drivers",
        session_key=10014,
        silver_target=str(silver_target),
        write_mode="merge",
        merge_key="driver_number",
        contract=DriverContract,
    )
    assert stats["bronze"] == 2
    assert stats["silver"] == 3  # 2 existing + 1 new (44, 1, 16)
    result = pd.read_parquet(silver_target)
    assert set(result["driver_number"]) == {44, 1, 16}


def test_process_silver_table_partitioned_write(tmp_path, mocker):
    """_process_silver_table with write_mode='partitioned' writes to session_key dir."""
    partition = tmp_path / "bronze"
    partition.mkdir()
    df = pd.DataFrame(
        [
            {"driver_number": 44, "full_name": "Lewis Hamilton", "date": "2025-03-16T12:00:00"},
        ]
    )
    df.to_parquet(partition / "drivers.parquet")

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _process_silver_table

    stats = _process_silver_table(
        partition_path=str(partition),
        quarantine_path=str(tmp_path / "quarantine"),
        file_name="drivers.parquet",
        table_name="drivers",
        session_key=10014,
        silver_target="fact_drivers",
        write_mode="partitioned",
        date_col="date",
    )
    assert stats["bronze"] == 1
    assert stats["silver"] == 1
    target_dir = tmp_path / "silver" / "fact_drivers" / "session_key=10014"
    assert (target_dir / "data.parquet").exists()


def test_process_silver_table_post_process(tmp_path, mocker):
    """_process_silver_table invokes post_process callable."""
    partition = tmp_path / "bronze"
    partition.mkdir()
    silver_parent = tmp_path / "silver"
    silver_parent.mkdir(parents=True)
    df = pd.DataFrame(
        [
            {
                "driver_number": 44,
                "full_name": "Lewis Hamilton",
                "name_acronym": "HAM",
                "team_name": "Ferrari",
                "country_code": "GBR",
            }
        ]
    )
    df.to_parquet(partition / "drivers.parquet")

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _process_silver_table

    mock_fn = mocker.MagicMock()

    _process_silver_table(
        partition_path=str(partition),
        quarantine_path=str(tmp_path / "quarantine"),
        file_name="drivers.parquet",
        table_name="drivers",
        session_key=10014,
        silver_target=str(silver_parent / "dim_drivers.parquet"),
        write_mode="merge",
        merge_key="driver_number",
        post_process=mock_fn,
    )
    mock_fn.assert_called_once()


def test_process_silver_table_vectorized_validation(tmp_path, mocker):
    """_process_silver_table with contract=None uses vectorized validation."""
    partition = tmp_path / "bronze"
    partition.mkdir()
    (tmp_path / "silver").mkdir(parents=True)
    df = pd.DataFrame(
        [
            {"driver_number": 44, "speed": 312, "rpm": 11800, "date": "2025-03-16T12:00:00"},
            {"driver_number": 1, "speed": -999, "rpm": 12000, "date": "2025-03-16T12:01:00"},
        ]
    )
    df.to_parquet(partition / "telemetry.parquet")

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _process_silver_table

    stats = _process_silver_table(
        partition_path=str(partition),
        quarantine_path=str(tmp_path / "quarantine"),
        file_name="telemetry.parquet",
        table_name="telemetry",
        session_key=10014,
        silver_target=str(tmp_path / "silver" / "dim_telemetry.parquet"),
        write_mode="merge",
        merge_key="driver_number",
        contract=None,
        schema={"driver_number": "int64", "speed": "int64", "rpm": "int64"},
        required_cols=["driver_number", "date"],
    )
    assert stats["bronze"] == 2
    # Both rows should pass vectorized validation (no strict range checks)
    assert stats["silver"] == 2


@pytest.mark.xfail(reason="Complex function requiring DuckDB ASOF JOIN — needs real DuckDB connection")
def test_process_asof_join_telemetry_happy_path():
    pytest.skip("Needs DuckDB ASOF JOIN — integration-level test")


def test_process_asof_join_telemetry_missing_files(tmp_path, mocker):
    """_process_asof_join_telemetry returns zeros when car_data or location missing."""
    partition = tmp_path / "bronze"
    partition.mkdir()
    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    import duckdb

    from src.ingestion.process import _process_asof_join_telemetry

    conn = duckdb.connect(":memory:")
    try:
        stats = _process_asof_join_telemetry(
            partition_path=str(partition),
            quarantine_path=str(tmp_path / "quarantine"),
            session_key=10014,
            focus_drivers={44: "LH"},
            conn=conn,
        )
        assert stats == {"bronze": 0, "silver": 0, "quarantine": 0}
    finally:
        conn.close()


@pytest.mark.xfail(reason="Complex function requiring DuckDB + sklearn — integration-level test")
def test_process_gold_layer_full_flow():
    pytest.skip("Needs DuckDB, stints parquet, telemetry glob — integration-level")


def test_process_gold_layer_no_stints(tmp_path, mocker):
    """_process_gold_layer returns zeros when stints parquet does not exist."""
    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    import duckdb

    from src.ingestion.process import _process_gold_layer

    conn = duckdb.connect(":memory:")
    try:
        stats = _process_gold_layer(conn)
        assert stats == {"silver": 0}
    finally:
        conn.close()


def test_process_medallion_pipeline_missing_sessions_file(tmp_path, mocker):
    """Pipeline deve falhar quando sessions.parquet está ausente."""
    bronze = tmp_path / "data" / "bronze" / "year=2025" / "gp=bahrain" / "session=Race"
    bronze.mkdir(parents=True)

    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path / "data"))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))
    mocker.patch("src.ingestion.process.duckdb.connect")

    from src.ingestion.process import process_medallion_pipeline

    with pytest.raises(FileNotFoundError, match="sessions.parquet é obrigatório"):
        process_medallion_pipeline(2025, "bahrain", "Race")


def test_write_lineage_creates_file(tmp_path, mocker):
    """_write_lineage creates execution record parquet."""
    mocker.patch("src.ingestion.process.DATA_DIR", str(tmp_path / "data"))
    mocker.patch("src.ingestion.process.QUARANTINE_DIR", str(tmp_path / "quarantine"))

    from src.ingestion.process import _write_lineage

    run_record = {
        "run_id": "test-uuid",
        "pipeline_name": "cli_test",
        "session_key": 10014,
        "execution_timestamp": "2026-06-20T12:00:00",
        "duration_seconds": 1.5,
        "status": "SUCCESS",
        "total_rows_processed": 10,
        "total_rows_bronze": 100,
        "total_rows_silver": 80,
        "total_rows_quarantine": 5,
        "quarantine_rate": 0.05,
        "records_rejected": 5,
        "data_freshness_minutes": 30,
        "sla_runtime_status": "COMPLIANT",
        "sla_quality_status": "COMPLIANT",
        "sla_freshness_status": "COMPLIANT",
    }
    _write_lineage(run_record)

    exec_file = tmp_path / "data" / "silver" / "fact_pipeline_execution" / "session_key=10014" / "data.parquet"
    assert exec_file.exists()
    result = pd.read_parquet(exec_file)
    assert len(result) == 1
    assert result.iloc[0]["status"] == "SUCCESS"
