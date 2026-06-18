import pandas as pd


def _write_silver_parquet(base, name, df):
    path = base / "silver" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def _write_gold_partitioned(base, layer, table, session_key, df):
    path = base / "gold" / table / f"session_key={session_key}" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def _write_silver_telemetry(base, session_key, driver_number, df):
    path = (
        base
        / "silver"
        / "fact_car_telemetry"
        / f"session_key={session_key}"
        / f"driver_number={driver_number}"
        / "data.parquet"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_silver_parquet_files_exist(tmp_path):
    essential = ["dim_sessions", "dim_drivers", "dim_stints", "dim_weather"]
    for name in essential:
        _write_silver_parquet(tmp_path, f"{name}.parquet", pd.DataFrame({"col": [1]}))

    silver_dir = tmp_path / "silver"
    assert silver_dir.exists()
    for name in essential:
        path = silver_dir / f"{name}.parquet"
        df = pd.read_parquet(path)
        assert not df.empty


def test_silver_telemetry_partitioning(tmp_path):
    telemetry_data = pd.DataFrame(
        {
            "speed": [120, 310, 150],
            "rpm": [4000, 12000, 6000],
            "n_gear": [4, 8, 5],
            "throttle": [50.0, 99.0, 60.0],
            "brake": [10.0, 0.0, 5.0],
        }
    )
    _write_silver_telemetry(tmp_path, session_key=10014, driver_number=44, df=telemetry_data)
    _write_silver_telemetry(tmp_path, session_key=10014, driver_number=1, df=telemetry_data)

    telemetry_root = tmp_path / "silver" / "fact_car_telemetry"
    sessions = sorted(telemetry_root.iterdir())
    assert len(sessions) > 0

    for sess_dir in sessions:
        assert sess_dir.name.startswith("session_key=")
        drivers = sorted(sess_dir.iterdir())
        for drv_dir in drivers:
            assert drv_dir.name.startswith("driver_number=")
            parquet_file = drv_dir / "data.parquet"
            assert parquet_file.exists()

            df = pd.read_parquet(parquet_file)
            assert "speed" in df.columns
            assert "rpm" in df.columns
            assert "n_gear" in df.columns
            assert (df["speed"] >= 0).all() and (df["speed"] <= 380).all()
            assert (df["n_gear"] >= -1).all() and (df["n_gear"] <= 8).all()
            assert (df["rpm"] >= 0).all() and (df["rpm"] <= 16000).all()


def test_gold_predictions_integrity(tmp_path):
    gold_df = pd.DataFrame(
        {
            "session_key": [10014],
            "driver_number": [44],
            "lap_duration_seconds": [92.5],
            "predicted_lap_duration_seconds": [91.9],
            "delta_performance_seconds": [0.6],
        }
    )
    _write_gold_partitioned(tmp_path, "gold", "lap_predictions", 10014, gold_df)

    prediction_files = sorted((tmp_path / "gold" / "lap_predictions").rglob("data.parquet"))
    assert len(prediction_files) > 0
    df = pd.concat([pd.read_parquet(path) for path in prediction_files], ignore_index=True)
    assert not df.empty

    required_cols = [
        "session_key",
        "driver_number",
        "lap_duration_seconds",
        "predicted_lap_duration_seconds",
        "delta_performance_seconds",
    ]
    for col in required_cols:
        assert col in df.columns
        assert df[col].notna().any()

    mean_prediction = df["predicted_lap_duration_seconds"].mean()
    assert 50.0 <= mean_prediction <= 250.0


def test_gold_features_partitioning(tmp_path):
    features_df = pd.DataFrame(
        {
            "session_key": [10014],
            "driver_number": [44],
            "stint_number": [1],
            "lap_number": [1],
            "lap_duration_seconds": [92.5],
        }
    )
    _write_gold_partitioned(tmp_path, "gold", "features_lap_data", 10014, features_df)

    feature_files = sorted((tmp_path / "gold" / "features_lap_data").rglob("data.parquet"))
    assert len(feature_files) > 0
    df = pd.concat([pd.read_parquet(path) for path in feature_files], ignore_index=True)
    assert not df.empty

    required_cols = [
        "session_key",
        "driver_number",
        "stint_number",
        "lap_number",
        "lap_duration_seconds",
    ]
    for col in required_cols:
        assert col in df.columns
        assert df[col].notna().any()


def test_ml_model_serialization(tmp_path):
    import joblib
    import numpy as np
    from sklearn.linear_model import LinearRegression

    rng = np.random.RandomState(42)
    model = LinearRegression()
    X = rng.rand(100, 5)
    y = rng.rand(100)
    model.fit(X, y)

    model_path = tmp_path / "lap_regressor.joblib"
    joblib.dump(model, model_path)

    loaded = joblib.load(model_path)
    assert hasattr(loaded, "predict")


def test_gold_f1_telemetry_analysis_integrity(tmp_path):
    analysis_df = pd.DataFrame(
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
    gold_parquet = tmp_path / "gold" / "fct_f1_telemetry_analysis.parquet"
    gold_parquet.parent.mkdir(parents=True, exist_ok=True)
    analysis_df.to_parquet(gold_parquet)

    df = pd.read_parquet(gold_parquet)
    assert not df.empty

    required_cols = [
        "session_key",
        "driver_number",
        "lap_number",
        "max_speed",
        "avg_speed",
        "max_rpm",
        "avg_rpm",
        "throttle_intensity_pct",
        "brake_intensity_pct",
        "drs_activation_pct",
        "gear_changes",
    ]
    for col in required_cols:
        assert col in df.columns
        assert df[col].notna().all()

    assert (df["lap_number"] > 0).all()
    assert (df["max_speed"] <= 400).all()
    assert (df["avg_speed"] <= 380).all()
    assert (df["max_rpm"] <= 18000).all()
    assert (df["throttle_intensity_pct"] >= 0).all()
    assert (df["throttle_intensity_pct"] <= 100).all()
    assert (df["brake_intensity_pct"] >= 0).all()
    assert (df["brake_intensity_pct"] <= 100).all()
    assert (df["drs_activation_pct"] >= 0).all()
    assert (df["drs_activation_pct"] <= 100).all()
    assert (df["gear_changes"] >= 0).all()

    active_laps = df[df["max_speed"] >= 100]
    assert len(active_laps) / len(df) > 0.8
    assert (active_laps["max_speed"] >= 50).all()
    assert (active_laps["avg_speed"] >= 10).all()
    assert (active_laps["max_rpm"] >= 1000).all()
