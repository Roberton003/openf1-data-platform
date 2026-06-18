"""Tests for web/model_loader.py — ModelLoader singleton with joblib fallback."""

import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from src.web.model_loader import ModelLoader, get_model_loader


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset ModelLoader singleton between tests."""
    ModelLoader._instance = None
    yield
    ModelLoader._instance = None


def test_model_loader_returns_model_from_joblib(tmp_path):
    model_file = tmp_path / "lap_regressor.joblib"
    model_file.write_text("fake model")
    loader = ModelLoader(joblib_path=str(model_file), cache_ttl=300)
    with patch("src.web.model_loader.joblib.load", return_value="loaded_model") as mock_load:
        result = loader.load()
        mock_load.assert_called_once()
        assert result == "loaded_model"


def test_model_loader_returns_none_when_no_model(tmp_path):
    loader = ModelLoader(joblib_path=str(tmp_path / "nonexistent.joblib"), cache_ttl=300)
    with patch("src.web.model_loader.ModelLoader._try_mlflow", return_value=None):
        result = loader.load()
        assert result is None


def test_model_loader_cache_returns_same_object(tmp_path):
    model_file = tmp_path / "lap_regressor.joblib"
    model_file.write_text("fake model")
    loader = ModelLoader(joblib_path=str(model_file), cache_ttl=300)
    with patch("src.web.model_loader.joblib.load", return_value="cached_model"):
        first = loader.load()
        second = loader.load()
        assert first is second


def test_model_loader_cache_expires(tmp_path):
    model_file = tmp_path / "lap_regressor.joblib"
    model_file.write_text("fake model")
    loader = ModelLoader(joblib_path=str(model_file), cache_ttl=0)
    call_count = 0

    def mock_load_side_effect(*a, **kw):
        nonlocal call_count
        call_count += 1
        return f"model_{call_count}"

    with patch("src.web.model_loader.joblib.load", side_effect=mock_load_side_effect):
        first = loader.load()
        second = loader.load()
        assert first != second
        assert call_count == 2


def test_get_model_loader_singleton():
    loader1 = get_model_loader()
    loader2 = get_model_loader()
    assert loader1 is loader2


def test_model_loader_thread_safety(tmp_path):
    model_file = tmp_path / "lap_regressor.joblib"
    model_file.write_text("fake model")
    loader = ModelLoader(joblib_path=str(model_file), cache_ttl=300)
    results = []

    with patch("src.web.model_loader.joblib.load", return_value="thread_model"):
        def load_model():
            results.append(loader.load())

        threads = [threading.Thread(target=load_model) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(results) == 5
    assert all(r == "thread_model" for r in results)
