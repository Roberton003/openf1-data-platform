"""
ModelLoader singleton — loads MLflow registry models with joblib fallback.
"""

import os
import threading
import time
from typing import Any

import joblib

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///data/mlflow/mlflow.db")
MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "lap_regressor")
DEFAULT_CACHE_TTL = int(os.environ.get("MODEL_CACHE_TTL_SECONDS", "300"))


class ModelLoader:
    """Thread-safe singleton that loads models from MLflow with joblib fallback."""

    _instance: "ModelLoader | None" = None
    _lock = threading.Lock()

    def __init__(
        self,
        mlflow_uri: str = MLFLOW_URI,
        joblib_path: str | None = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        self.mlflow_uri = mlflow_uri
        self.joblib_path = joblib_path or os.path.join(MODELS_DIR, "lap_regressor.joblib")
        self.cache_ttl = cache_ttl
        self._model: Any = None
        self._loaded_at: float = 0.0
        self._load_lock = threading.Lock()

    def load(self) -> Any:
        now = time.monotonic()
        if self._model is not None and (now - self._loaded_at) < self.cache_ttl:
            return self._model

        with self._load_lock:
            if self._model is not None and (now - self._loaded_at) < self.cache_ttl:
                return self._model

            model = self._try_mlflow()
            if model is None:
                model = self._try_joblib()
            self._model = model
            self._loaded_at = time.monotonic()
            return model

    def _try_mlflow(self) -> Any:
        try:
            import mlflow

            mlflow.set_tracking_uri(self.mlflow_uri)
            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])
            if not latest:
                return None
            model_uri = f"models:/{MODEL_NAME}/Production"
            return mlflow.sklearn.load_model(model_uri)
        except Exception:
            return None

    def _try_joblib(self) -> Any:
        if os.path.exists(self.joblib_path):
            return joblib.load(self.joblib_path)
        return None


def get_model_loader(**kwargs: Any) -> ModelLoader:
    if ModelLoader._instance is None:
        with ModelLoader._lock:
            if ModelLoader._instance is None:
                ModelLoader._instance = ModelLoader(**kwargs)
    return ModelLoader._instance
