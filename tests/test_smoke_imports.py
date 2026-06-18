"""
Import safety net — confirm all new dependencies load correctly and no
critical module breaks on import.
"""

import pytest


def test_chromadb_import():
    import chromadb

    assert hasattr(chromadb, "PersistentClient")


def test_sentence_transformers_import():
    import sentence_transformers

    assert hasattr(sentence_transformers, "SentenceTransformer")


@pytest.mark.slow
def test_sentence_transformers_model():
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(["test"], normalize_embeddings=True)
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384


def test_mlflow_import():
    import mlflow

    assert hasattr(mlflow, "start_run")
    assert hasattr(mlflow, "log_metrics")
    assert hasattr(mlflow, "register_model")


def test_sklearn_imports_still_function():
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression

    assert RandomForestRegressor
    assert LinearRegression
