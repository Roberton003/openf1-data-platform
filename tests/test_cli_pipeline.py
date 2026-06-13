from unittest.mock import patch

import pandas as pd

from src.ingestion.process import process_medallion_pipeline


def test_cli_pipeline_execution(tmp_path):
    # Criar estruturas de pastas temporárias mock
    data_dir = tmp_path / "data"
    bronze_dir = data_dir / "bronze" / "year=2025" / "gp=Bahrain" / "session=Race"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    # Criar dados mínimos de Bronze
    # 1. Sessions
    sessions_df = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "year": 2025,
                "session_name": "Race",
                "session_type": "Race",
                "circuit_key": 12,
                "circuit_short_name": "Bahrain GP",
                "country_name": "Bahrain",
            }
        ]
    )
    sessions_df.to_parquet(bronze_dir / "sessions.parquet", index=False)

    # 2. Drivers
    drivers_df = pd.DataFrame(
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
    drivers_df.to_parquet(bronze_dir / "drivers.parquet", index=False)

    # 3. Stints
    stints_df = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 1,
                "stint_number": 1,
                "compound": "MEDIUM",
                "lap_start": 1,
                "lap_end": 10,
                "tyre_age_at_start": 0,
            }
        ]
    )
    stints_df.to_parquet(bronze_dir / "stints.parquet", index=False)

    # Patch de DATA_DIR no process.py para apontar para tmp_path/data
    with patch("src.ingestion.process.DATA_DIR", str(data_dir)):
        process_medallion_pipeline(2025, "Bahrain", "Race")

    # Verificar se os Parquets da Silver foram gravados nas pastas corretas
    silver_dir = data_dir / "silver"
    assert (silver_dir / "dim_sessions.parquet").exists()
    assert (silver_dir / "dim_drivers.parquet").exists()
    assert (silver_dir / "dim_stints.parquet").exists()

    # Verificar se as tabelas de fatos foram criadas como partições
    assert (
        silver_dir / "fact_pipeline_execution" / "session_key=10014" / "data.parquet"
    ).exists()
