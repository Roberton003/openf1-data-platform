"""
Tests for MLflow integration — API availability and metrics.
"""


def test_mlflow_import_and_api():
    import mlflow

    assert hasattr(mlflow, "start_run")
    assert hasattr(mlflow, "log_metrics")
    assert hasattr(mlflow, "register_model")
    assert hasattr(mlflow, "sklearn")


def test_mlflow_metrics_work():
    import numpy as np
    from sklearn.metrics import (mean_absolute_error, mean_squared_error,
                                 r2_score)

    y_true = np.array([90.0, 92.0, 88.0])
    y_pred = np.array([91.0, 91.5, 89.0])

    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    assert isinstance(mse, float)
    assert isinstance(mae, float)
    assert isinstance(r2, float)
    assert mse >= 0
