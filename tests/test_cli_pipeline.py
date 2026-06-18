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

    # 3. Stints (MEDIUM + HARD + WET for compound variation)
    stints_df = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 1,
                "stint_number": 1,
                "compound": "MEDIUM",
                "lap_start": 1,
                "lap_end": 5,
                "tyre_age_at_start": 0,
            },
            {
                "session_key": 10014,
                "driver_number": 1,
                "stint_number": 2,
                "compound": "HARD",
                "lap_start": 6,
                "lap_end": 10,
                "tyre_age_at_start": 0,
            },
            {
                "session_key": 10014,
                "driver_number": 44,
                "stint_number": 1,
                "compound": "MEDIUM",
                "lap_start": 1,
                "lap_end": 10,
                "tyre_age_at_start": 0,
            },
        ]
    )
    stints_df.to_parquet(bronze_dir / "stints.parquet", index=False)

    # 4. Telemetry (car_data) — needed for Gold section
    car_data_df = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 1,
                "date": "2025-03-16T12:00:00.000",
                "speed": 320,
                "rpm": 12100,
                "n_gear": 8,
                "throttle": 100.0,
                "brake": 0.0,
                "drs": 12,
            },
            {
                "session_key": 10014,
                "driver_number": 44,
                "date": "2025-03-16T12:00:00.000",
                "speed": 312,
                "rpm": 11800,
                "n_gear": 7,
                "throttle": 98.5,
                "brake": 0.0,
                "drs": 12,
            },
        ]
    )
    car_data_df.to_parquet(bronze_dir / "car_data.parquet", index=False)

    # 5. Location — needed for Silver telemetry ASOF JOIN
    location_df = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 1,
                "date": "2025-03-16T12:00:00.000",
                "x": 100,
                "y": 200,
                "z": 0,
            },
            {
                "session_key": 10014,
                "driver_number": 44,
                "date": "2025-03-16T12:00:00.000",
                "x": 110,
                "y": 210,
                "z": 0,
            },
        ]
    )
    location_df.to_parquet(bronze_dir / "location.parquet", index=False)

    # Patch de DATA_DIR no process.py para apontar para tmp_path/data
    with patch("src.ingestion.process.DATA_DIR", str(data_dir)):
        process_medallion_pipeline(2025, "Bahrain", "Race")

    # Verificar Silver
    silver_dir = data_dir / "silver"
    assert (silver_dir / "dim_sessions.parquet").exists()
    assert (silver_dir / "dim_drivers.parquet").exists()
    assert (silver_dir / "dim_stints.parquet").exists()
    assert (silver_dir / "fact_pipeline_execution" / "session_key=10014" / "data.parquet").exists()
    assert (silver_dir / "fact_car_telemetry" / "session_key=10014" / "driver_number=1" / "data.parquet").exists()

    # Verificar Gold
    gold_dir = data_dir / "gold"
    features_dir = gold_dir / "features_lap_data" / "session_key=10014"
    assert features_dir.exists()
    assert any(features_dir.iterdir()), "features_lap_data should have files"

    predictions_dir = gold_dir / "lap_predictions" / "session_key=10014"
    assert predictions_dir.exists()
    assert any(predictions_dir.iterdir()), "lap_predictions should have files"

    # Verificar modelo serializado
    model_path = data_dir.parent / "models" / "lap_regressor.joblib"
    assert model_path.exists(), "Model joblib should exist"

    import joblib

    model = joblib.load(model_path)
    assert hasattr(model, "predict")

    # Verificar que features têm colunas esperadas
    feat_files = sorted(features_dir.rglob("*.parquet"))
    df_feat = pd.concat([pd.read_parquet(f) for f in feat_files], ignore_index=True)
    assert "lap_number" in df_feat.columns
    assert "lap_duration_seconds" in df_feat.columns
    assert "compound" in df_feat.columns
    assert df_feat["compound"].nunique() >= 2, "Multiple compounds should be present"
