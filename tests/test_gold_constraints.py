import pandas as pd
import pytest

from src.ingestion.schemas import GOLD_TABLE_CONSTRAINTS, validate_gold_constraints


def test_known_table_definitions():
    assert "fct_f1_telemetry_analysis" in GOLD_TABLE_CONSTRAINTS
    assert "gold_features_lap_data" in GOLD_TABLE_CONSTRAINTS
    assert "gold_lap_predictions" in GOLD_TABLE_CONSTRAINTS


def test_unknown_table_returns_violation():
    df = pd.DataFrame({"a": [1]})
    violations = validate_gold_constraints(df, "unknown_table")
    assert len(violations) == 1
    assert "Unknown" in violations[0]


def test_telemetry_analysis_passes():
    df = pd.DataFrame(
        {
            "session_key": [10014, 10014],
            "driver_number": [44, 1],
            "lap_number": [1, 2],
            "max_speed": [312, 298],
            "avg_speed": [280.5, 265.0],
            "max_rpm": [11800, 11500],
            "avg_rpm": [11000.0, 10800.0],
            "throttle_intensity_pct": [98.5, 92.0],
            "brake_intensity_pct": [0.0, 5.0],
            "drs_activation_pct": [10.0, 8.0],
            "gear_changes": [15, 12],
        }
    )
    violations = validate_gold_constraints(df, "fct_f1_telemetry_analysis")
    assert violations == []


def test_telemetry_analysis_null_violation():
    df = pd.DataFrame(
        {
            "session_key": [10014, None],
            "driver_number": [44, 1],
            "lap_number": [1, 2],
        }
    )
    violations = validate_gold_constraints(df, "fct_f1_telemetry_analysis")
    null_violations = [v for v in violations if "null" in v.lower()]
    assert len(null_violations) > 0


def test_telemetry_analysis_range_violation():
    df = pd.DataFrame(
        {
            "session_key": [10014],
            "driver_number": [44],
            "lap_number": [1],
            "max_speed": [999],
            "avg_speed": [280.5],
            "max_rpm": [11800],
            "avg_rpm": [11000.0],
            "throttle_intensity_pct": [98.5],
            "brake_intensity_pct": [0.0],
            "drs_activation_pct": [10.0],
            "gear_changes": [15],
        }
    )
    violations = validate_gold_constraints(df, "fct_f1_telemetry_analysis")
    range_violations = [v for v in violations if "above maximum" in v]
    assert any("max_speed" in v for v in range_violations)


def test_features_lap_data_passes():
    df = pd.DataFrame(
        {
            "session_key": [10014],
            "driver_number": [44],
            "stint_number": [1],
            "lap_number": [1],
            "lap_duration_seconds": [92.5],
            "max_speed": [312],
            "max_rpm": [11800],
            "throttle_intensity_pct": [98.5],
            "brake_intensity_pct": [0.0],
        }
    )
    violations = validate_gold_constraints(df, "gold_features_lap_data")
    assert violations == []


def test_lap_predictions_passes():
    df = pd.DataFrame(
        {
            "session_key": [10014],
            "driver_number": [44],
            "lap_duration_seconds": [92.5],
            "predicted_lap_duration_seconds": [91.9],
            "delta_performance_seconds": [0.6],
        }
    )
    violations = validate_gold_constraints(df, "gold_lap_predictions")
    assert violations == []


def test_lap_predictions_delta_range():
    df = pd.DataFrame(
        {
            "session_key": [10014],
            "driver_number": [44],
            "lap_duration_seconds": [92.5],
            "predicted_lap_duration_seconds": [91.9],
            "delta_performance_seconds": [999.0],
        }
    )
    violations = validate_gold_constraints(df, "gold_lap_predictions")
    assert any("delta_performance_seconds" in v for v in violations)


@pytest.mark.parametrize("table", GOLD_TABLE_CONSTRAINTS.keys())
def test_empty_dataframe_returns_not_null_violations(table):
    df = pd.DataFrame()
    violations = validate_gold_constraints(df, table)
    not_null_cols = GOLD_TABLE_CONSTRAINTS[table]["not_null_cols"]
    expected_count = len(not_null_cols)
    assert len(violations) == expected_count
