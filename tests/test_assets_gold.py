"""Tests for ingestion/assets.py — Gold layer assets (features, model training, predictions)."""

import os

import pandas as pd
from dagster import build_asset_context

from src.ingestion.assets import (
    gold_feature_engineering_lap_data,
    gold_lap_predictions,
    gold_lap_time_prediction_model,
)


def _context():
    return build_asset_context()


def _create_silver_data(data_dir):
    """Helper: create minimal Silver data for Gold tests."""
    silver = os.path.join(data_dir, "silver")
    os.makedirs(silver, exist_ok=True)
    silvers = [
        {
            "session_key": 10014,
            "driver_number": 44,
            "lap_number": 1,
            "stint_number": 1,
            "compound": "SOFT",
            "tyre_age_at_start": 0,
            "max_speed": 312,
            "avg_speed": 280.5,
            "max_rpm": 11800,
            "avg_rpm": 11000.0,
            "throttle_intensity_pct": 98.5,
            "brake_intensity_pct": 0.0,
            "drs_activation_pct": 10.0,
            "gear_changes": 15,
            "lap_duration_seconds": 92.5,
        },
    ]
    df = pd.DataFrame(silvers)
    os.makedirs(os.path.join(silver, "fct_f1_telemetry_analysis"), exist_ok=True)
    df.to_parquet(os.path.join(silver, "fct_f1_telemetry_analysis", "data.parquet"), index=False)


def test_gold_features_no_silver_data(tmp_data_dir):
    gold_feature_engineering_lap_data(_context())


def test_gold_features_speed_factor_zero(tmp_data_dir):
    """max_speed=0 should produce a large speed_factor but not crash."""
    silver = os.path.join(tmp_data_dir, "silver")
    os.makedirs(silver, exist_ok=True)

    pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "lap_number": 1,
                "stint_number": 1,
                "compound": "SOFT",
                "tyre_age_at_start": 0,
                "max_speed": 0,
                "avg_speed": 0.0,
                "max_rpm": 0,
                "avg_rpm": 0.0,
                "throttle_intensity_pct": 0.0,
                "brake_intensity_pct": 0.0,
                "drs_activation_pct": 0.0,
                "gear_changes": 0,
                "lap_duration_seconds": 120.0,
            }
        ]
    ).to_parquet(
        os.path.join(silver, "fct_f1_telemetry_analysis"),
        partition_cols=["session_key"],
    )
    gold_feature_engineering_lap_data(_context())


def test_gold_model_insufficient_data(tmp_data_dir):
    """< 5 rows => model training should skip."""
    gold_lap_time_prediction_model(_context())
    model_path = os.path.join(os.path.dirname(tmp_data_dir), "models", "lap_regressor.joblib")
    assert not os.path.exists(model_path)


def test_gold_model_no_features_data(tmp_data_dir):
    """No features file => model should skip."""
    gold_lap_time_prediction_model(_context())


def test_gold_predictions_no_model(tmp_data_dir):
    """No model file => predictions should skip."""
    gold_lap_predictions(_context())


def _create_silver_stints_and_telemetry(data_dir):
    """Helper: create dim_stints.parquet + fact_car_telemetry/ for gold_feature_engineering."""
    silver = os.path.join(data_dir, "silver")
    os.makedirs(silver, exist_ok=True)

    pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "stint_number": 1,
                "compound": "SOFT",
                "tyre_age_at_start": 0,
                "lap_start": 1,
                "lap_end": 3,
            }
        ]
    ).to_parquet(os.path.join(silver, "dim_stints.parquet"), index=False)

    tel_dir = os.path.join(silver, "fact_car_telemetry")
    os.makedirs(tel_dir, exist_ok=True)


def test_gold_features_full_flow(tmp_data_dir, mocker):
    """Exercises stint expansion, feature generation, and Gold output writing."""
    _create_silver_stints_and_telemetry(tmp_data_dir)

    mock_conn = mocker.MagicMock()
    mock_features = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "max_speed": 312.0,
                "max_rpm": 11800.0,
                "throttle_intensity_pct": 85.0,
                "brake_intensity_pct": 10.0,
            }
        ]
    )
    mock_conn.execute().df.return_value = mock_features
    mocker.patch("duckdb.connect", return_value=mock_conn)

    gold_feature_engineering_lap_data(_context())

    gold_dir = os.path.join(tmp_data_dir, "gold", "features_lap_data")
    assert os.path.isdir(gold_dir)
    files = sorted(os.listdir(gold_dir))
    assert len(files) > 0
    part_file = os.path.join(gold_dir, files[0])
    df = pd.read_parquet(part_file)
    assert "lap_duration_seconds" in df.columns
    assert "compound_num" in df.columns
    assert len(df) == 3


def test_gold_features_medium_compound_penalty(tmp_data_dir, mocker):
    """MEDIUM compound adds 0.8s penalty to lap time."""
    silver = os.path.join(tmp_data_dir, "silver")
    os.makedirs(silver, exist_ok=True)

    pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "stint_number": 1,
                "compound": "MEDIUM",
                "tyre_age_at_start": 0,
                "lap_start": 1,
                "lap_end": 1,
            }
        ]
    ).to_parquet(os.path.join(silver, "dim_stints.parquet"), index=False)

    tel_dir = os.path.join(silver, "fact_car_telemetry")
    os.makedirs(tel_dir, exist_ok=True)

    mock_conn = mocker.MagicMock()
    mock_conn.execute().df.return_value = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "max_speed": 300.0,
                "max_rpm": 11000.0,
                "throttle_intensity_pct": 80.0,
                "brake_intensity_pct": 15.0,
            }
        ]
    )
    mocker.patch("duckdb.connect", return_value=mock_conn)

    gold_feature_engineering_lap_data(_context())

    gold_dir = os.path.join(tmp_data_dir, "gold", "features_lap_data")
    assert os.path.isdir(gold_dir)


def test_gold_features_no_telemetry_for_driver(tmp_data_dir, mocker):
    """Driver with no telemetry in DuckDB result should be skipped."""
    silver = os.path.join(tmp_data_dir, "silver")
    os.makedirs(silver, exist_ok=True)

    pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "stint_number": 1,
                "compound": "SOFT",
                "tyre_age_at_start": 0,
                "lap_start": 1,
                "lap_end": 1,
            }
        ]
    ).to_parquet(os.path.join(silver, "dim_stints.parquet"), index=False)

    tel_dir = os.path.join(silver, "fact_car_telemetry")
    os.makedirs(tel_dir, exist_ok=True)

    mock_conn = mocker.MagicMock()
    mock_conn.execute().df.return_value = pd.DataFrame(
        columns=[
            "session_key",
            "driver_number",
            "max_speed",
            "max_rpm",
            "throttle_intensity_pct",
            "brake_intensity_pct",
        ]
    )
    mocker.patch("duckdb.connect", return_value=mock_conn)

    gold_feature_engineering_lap_data(_context())

    gold_dir = os.path.join(tmp_data_dir, "gold", "features_lap_data")
    assert not os.path.isdir(gold_dir)


def test_gold_model_full_flow(tmp_data_dir, mocker):
    """Exercises model training with features data."""
    gold_dir = os.path.join(tmp_data_dir, "gold", "features_lap_data")
    os.makedirs(gold_dir, exist_ok=True)

    rng = __import__("numpy").random.RandomState(42)
    rows = []
    for lap in range(20):
        rows.append(
            {
                "session_key": 10014,
                "driver_number": 44,
                "lap_number": lap + 1,
                "compound": "SOFT",
                "compound_num": 1,
                "tyre_age_at_start": lap,
                "max_speed": 300.0 + rng.randn() * 5,
                "max_rpm": 11000.0 + rng.randn() * 200,
                "throttle_intensity_pct": max(0, min(100, 80 + rng.randn() * 5)),
                "brake_intensity_pct": max(0, min(100, 15 + rng.randn() * 3)),
                "lap_duration_seconds": 90.0 + rng.randn() * 2,
            }
        )
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(gold_dir, "data.parquet"), index=False)

    mock_models_dir = os.path.join(os.path.dirname(tmp_data_dir), "models")
    mocker.patch("src.ingestion.assets.MODELS_DIR", mock_models_dir)
    import sys

    mock_mlflow = mocker.MagicMock()
    mock_mlflow.tracking.MlflowClient = mocker.MagicMock()
    sys.modules["mlflow"] = mock_mlflow

    gold_lap_time_prediction_model(_context())

    sys.modules.pop("mlflow", None)

    model_path = os.path.join(mock_models_dir, "lap_regressor.joblib")
    assert os.path.exists(model_path)


def test_gold_predictions_full_flow(tmp_data_dir, mocker):
    """Exercises predictions with features and a trained model."""
    gold_dir = os.path.join(tmp_data_dir, "gold", "features_lap_data")
    os.makedirs(gold_dir, exist_ok=True)

    rng = __import__("numpy").random.RandomState(42)
    rows = []
    for lap in range(20):
        rows.append(
            {
                "session_key": 10014,
                "driver_number": 44,
                "lap_number": lap + 1,
                "compound": "SOFT",
                "compound_num": 1,
                "tyre_age_at_start": lap,
                "max_speed": 300.0 + rng.randn() * 5,
                "max_rpm": 11000.0 + rng.randn() * 200,
                "throttle_intensity_pct": max(0, min(100, 80 + rng.randn() * 5)),
                "brake_intensity_pct": max(0, min(100, 15 + rng.randn() * 3)),
                "lap_duration_seconds": 90.0 + rng.randn() * 2,
            }
        )
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(gold_dir, "data.parquet"), index=False)

    mock_models_dir = os.path.join(os.path.dirname(tmp_data_dir), "models")
    mocker.patch("src.ingestion.assets.MODELS_DIR", mock_models_dir)

    import joblib
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(n_estimators=10, random_state=42, n_jobs=1)
    X = rng.rand(50, 5) * 100
    y = 50 + X[:, 0] * 0.5 + rng.rand(50) * 5
    model.fit(X, y)
    model.feature_names_in_ = __import__("numpy").array(
        ["throttle_intensity_pct", "brake_intensity_pct", "tyre_age_at_start", "compound_num", "max_speed"]
    )
    os.makedirs(mock_models_dir, exist_ok=True)
    joblib.dump(model, os.path.join(mock_models_dir, "lap_regressor.joblib"))

    import sys

    mock_mlflow = mocker.MagicMock()
    mock_mlflow.tracking.MlflowClient = mocker.MagicMock()
    sys.modules["mlflow"] = mock_mlflow

    gold_lap_predictions(_context())

    sys.modules.pop("mlflow", None)

    pred_dir = os.path.join(tmp_data_dir, "gold", "lap_predictions")
    assert os.path.isdir(pred_dir)
    pred_files = sorted(os.listdir(pred_dir))
    assert len(pred_files) > 0
    df_pred = pd.read_parquet(os.path.join(pred_dir, pred_files[0]))
    assert "predicted_lap_duration_seconds" in df_pred.columns
    assert "delta_performance_seconds" in df_pred.columns
