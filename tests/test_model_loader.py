"""
Tests for the ModelLoader singleton with MLflow + joblib fallback.
"""


def test_model_loader_joblib_fallback(tmp_path):
    from src.web.model_loader import ModelLoader

    model_path = tmp_path / "lap_regressor.joblib"
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(n_estimators=5, random_state=42)
    model.fit(np.random.rand(10, 5), np.random.rand(10))
    joblib.dump(model, model_path)

    loader = ModelLoader(mlflow_uri="nonexistent://uri", joblib_path=str(model_path), cache_ttl=0)
    loaded = loader.load()
    assert loaded is not None
    import numpy as np

    pred = loaded.predict(np.random.rand(1, 5))
    assert len(pred) == 1


def test_model_loader_no_model_returns_none(tmp_path):
    from src.web.model_loader import ModelLoader

    loader = ModelLoader(
        mlflow_uri="nonexistent://uri",
        joblib_path=str(tmp_path / "nonexistent.joblib"),
        cache_ttl=0,
    )
    assert loader.load() is None


def test_model_loader_singleton():
    from src.web.model_loader import get_model_loader

    loader1 = get_model_loader(mlflow_uri="test://uri")
    loader2 = get_model_loader()
    assert loader1 is loader2


def test_model_loader_cache_ttl(tmp_path):
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor

    from src.web.model_loader import ModelLoader

    model_path = tmp_path / "lap_regressor.joblib"
    model = RandomForestRegressor(n_estimators=5, random_state=42)
    model.fit(np.random.rand(10, 5), np.random.rand(10))
    joblib.dump(model, model_path)

    loader = ModelLoader(mlflow_uri="nonexistent://uri", joblib_path=str(model_path), cache_ttl=3600)
    m1 = loader.load()
    assert m1 is not None
    m2 = loader.load()
    assert m2 is m1
