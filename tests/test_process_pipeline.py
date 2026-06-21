"""Tests for process.py — CLI entry point and process_medallion_pipeline integration."""

import os

import pandas as pd
import pytest


@pytest.fixture
def minimal_bronze(tmp_path):
    """Create a minimal Bronze directory with one session's data."""
    bronze = tmp_path / "data" / "bronze" / "year=2025" / "gp=bahrain" / "session=Race"
    bronze.mkdir(parents=True)
    sessions = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "year": 2025,
                "session_name": "Race",
                "session_type": "Race",
                "circuit_key": 12,
                "circuit_short_name": "Bahrain GP",
                "country_name": "Bahrain",
                "date_start": "2025-03-16T12:00:00",
                "date_end": "2025-03-16T14:00:00",
                "gmt_offset": "03:00",
                "location": "Bahrain",
            }
        ]
    )
    sessions.to_parquet(bronze / "sessions.parquet")
    drivers = pd.DataFrame(
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
    drivers.to_parquet(bronze / "drivers.parquet")
    return str(tmp_path / "data")


def test_process_medallion_pipeline_partition_not_found():
    """Pipeline deve levantar FileNotFoundError quando partição não existe."""
    from src.ingestion.process import process_medallion_pipeline

    with pytest.raises(FileNotFoundError, match="Caminho da partição Bronze não encontrado"):
        process_medallion_pipeline(2099, "nonexistent", "Race", None)


def test_process_medallion_pipeline_minimal_flow(minimal_bronze, mocker):
    """Pipeline executa fluxo mínimo: lê Bronze, valida, escreve Silver."""
    mocker.patch("src.ingestion.process.DATA_DIR", minimal_bronze)
    mocker.patch("src.ingestion.process.duckdb.connect")
    mocker.patch("src.ingestion.process.index_race_control_messages")

    from src.ingestion.process import process_medallion_pipeline

    process_medallion_pipeline(2025, "bahrain", "Race", None)

    silver = os.path.join(minimal_bronze, "silver")
    assert os.path.exists(os.path.join(silver, "dim_sessions.parquet")), "dim_sessions deve ser criado"
    assert os.path.exists(os.path.join(silver, "dim_drivers.parquet")), "dim_drivers deve ser criado"


def test_process_medallion_pipeline_error_creates_lineage(minimal_bronze, mocker):
    """Pipeline que falha deve gravar linhagem FAILED."""
    mocker.patch("src.ingestion.process.DATA_DIR", minimal_bronze)
    mocker.patch("src.ingestion.process.validate_pydantic_batch", side_effect=ValueError("Mock validation error"))
    mocker.patch("src.ingestion.process.duckdb.connect")

    from src.ingestion.process import process_medallion_pipeline

    with pytest.raises(ValueError, match="Mock validation error"):
        process_medallion_pipeline(2025, "bahrain", "Race", None)

    exec_dir = os.path.join(minimal_bronze, "silver", "fact_pipeline_execution", "session_key=0")
    assert os.path.exists(os.path.join(exec_dir, "data.parquet")), (
        "FAILED lineage record must be written (session_key defaults to 0 when error occurs before assignment)"
    )


@pytest.fixture
def bronze_2024(tmp_path):
    """Create Bronze directory with 2024 data only (for fallback test)."""
    bronze = tmp_path / "data" / "bronze" / "year=2024" / "gp=bahrain" / "session=Race"
    bronze.mkdir(parents=True)
    sessions = pd.DataFrame(
        [
            {
                "session_key": 9979,
                "year": 2024,
                "session_name": "Race",
                "session_type": "Race",
                "circuit_key": 12,
                "circuit_short_name": "Bahrain GP",
                "country_name": "Bahrain",
                "date_start": "2024-03-16T12:00:00",
                "date_end": "2024-03-16T14:00:00",
                "gmt_offset": "03:00",
                "location": "Bahrain",
            }
        ]
    )
    sessions.to_parquet(bronze / "sessions.parquet")
    drivers = pd.DataFrame(
        [
            {
                "driver_number": 44,
                "full_name": "Lewis Hamilton",
                "name_acronym": "HAM",
                "team_name": "Mercedes",
                "country_code": "GBR",
            },
        ]
    )
    drivers.to_parquet(bronze / "drivers.parquet")
    return str(tmp_path / "data")


def test_process_medallion_pipeline_fallback_2024(bronze_2024, mocker):
    """Pipeline faz fallback de 2025 para 2024 quando partição 2025 não existe."""
    mocker.patch("src.ingestion.process.DATA_DIR", bronze_2024)
    mocker.patch("src.ingestion.process.duckdb.connect")
    mocker.patch("src.ingestion.process.index_race_control_messages")

    from src.ingestion.process import process_medallion_pipeline

    process_medallion_pipeline(2025, "bahrain", "Race", None)

    silver = os.path.join(bronze_2024, "silver")
    assert os.path.exists(os.path.join(silver, "dim_sessions.parquet"))


def test_run_cli_all_flag_no_partitions(mocker):
    """CLI --gp all sem partições deve logar e não processar."""
    mocker.patch("glob.glob", return_value=[])
    mocker.patch("src.ingestion.process.DATA_DIR", "/tmp/fake")

    mock_pipeline = mocker.patch("src.ingestion.process.process_medallion_pipeline")

    from src.ingestion.process import run_cli

    class MockArgs:
        year = 2025
        gp = "all"
        session = "Race"
        focus_drivers = None

    run_cli(MockArgs())
    assert not mock_pipeline.called


def test_run_cli_all_flag_with_partitions(mocker):
    """CLI --gp all com glob encontra partições e processa."""
    mocker.patch("glob.glob", return_value=["/tmp/data/bronze/year=2025/gp=bahrain/session=Race"])
    mocker.patch("src.ingestion.process.DATA_DIR", "/tmp/fake")

    mock_pipeline = mocker.patch("src.ingestion.process.process_medallion_pipeline")

    from src.ingestion.process import run_cli

    class MockArgs:
        year = 2025
        gp = "all"
        session = "Race"
        focus_drivers = None

    run_cli(MockArgs())
    assert mock_pipeline.called


def test_run_cli_single_gp(mocker):
    """CLI com --gp específico chama process_medallion_pipeline diretamente."""
    mocker.patch("src.ingestion.process.DATA_DIR", "/tmp/fake")

    mock_pipeline = mocker.patch("src.ingestion.process.process_medallion_pipeline")

    from src.ingestion.process import run_cli

    class MockArgs:
        year = 2025
        gp = "bahrain"
        session = "Race"
        focus_drivers = "1:Max Verstappen"

    run_cli(MockArgs())
    mock_pipeline.assert_called_once_with(2025, "bahrain", "Race", {1: "Max Verstappen"})
