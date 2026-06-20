"""Tests for ingestion/assets.py — Gold layer assets (features, model training, predictions)."""

import os

import pandas as pd
import pytest
from dagster import build_asset_context

from src.ingestion.assets import (
    gold_feature_engineering_lap_data,
    gold_lap_time_prediction_model,
    gold_lap_predictions,
)


def _context():
    return build_asset_context()


def _create_silver_data(data_dir):
    """Helper: create minimal Silver data for Gold tests."""
    silver = os.path.join(data_dir, "silver")
    os.makedirs(silver, exist_ok=True)
    silvers = [
        {"session_key": 10014, "driver_number": 44, "lap_number": 1,
         "stint_number": 1, "compound": "SOFT", "tyre_age_at_start": 0,
         "max_speed": 312, "avg_speed": 280.5, "max_rpm": 11800,
         "avg_rpm": 11000.0, "throttle_intensity_pct": 98.5,
         "brake_intensity_pct": 0.0, "drs_activation_pct": 10.0,
         "gear_changes": 15, "lap_duration_seconds": 92.5},
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

    pd.DataFrame([{
        "session_key": 10014, "driver_number": 44,
        "lap_number": 1, "stint_number": 1,
        "compound": "SOFT", "tyre_age_at_start": 0,
        "max_speed": 0, "avg_speed": 0.0,
        "max_rpm": 0, "avg_rpm": 0.0,
        "throttle_intensity_pct": 0.0, "brake_intensity_pct": 0.0,
        "drs_activation_pct": 0.0, "gear_changes": 0,
        "lap_duration_seconds": 120.0,
    }]).to_parquet(
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
