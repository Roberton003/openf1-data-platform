"""
Tests for the ChromaDB-backed vector store.
"""

import pandas as pd
import pytest


def _clear_vs_cache():
    import src.ingestion.vector_store as vs

    vs._COLLECTION_CACHE.clear()


def test_get_race_control_collection_cached(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection

    c1 = get_race_control_collection()
    c2 = get_race_control_collection()
    assert c1 is c2


def test_query_empty_collection_returns_empty(chroma_client, mocker):
    import src.ingestion.vector_store as vs

    vs._COLLECTION_CACHE.clear()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    results = vs.query_race_control(10014, "test")
    assert results == []


def test_index_without_message_column(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection, index_race_control_messages

    df = pd.DataFrame({"other_col": ["x"]})
    index_race_control_messages(10014, df)
    assert get_race_control_collection().count() == 1


def test_index_without_date_column(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection, index_race_control_messages

    df = pd.DataFrame({"message": ["test"]})
    index_race_control_messages(10014, df)
    assert get_race_control_collection().count() == 1


def test_index_replaces_existing(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection, index_race_control_messages

    df = pd.DataFrame({"message": ["first"]})
    index_race_control_messages(10014, df)
    assert get_race_control_collection().count() == 1
    index_race_control_messages(10014, df)
    assert get_race_control_collection().count() == 1


@pytest.mark.slow
def test_index_and_query_race_control(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection, index_race_control_messages

    df = pd.DataFrame(
        {
            "message": ["Green flag", "Yellow flag debris", "Safety car deployed"],
            "driver_number": [44, 1, 44],
            "category": ["Flag", "Flag", "Flag"],
            "flag": ["GREEN", "YELLOW", "SAFETY_CAR"],
            "date": pd.to_datetime(["2025-03-16 12:00:00", "2025-03-16 12:05:00", "2025-03-16 12:10:00"]),
        }
    )
    index_race_control_messages(10014, df)

    collection = get_race_control_collection()
    assert collection.count() == 3


def test_index_empty_dataframe(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection, index_race_control_messages

    df_empty = pd.DataFrame()
    index_race_control_messages(10014, df_empty)
    collection = get_race_control_collection()
    assert collection.count() == 0


def test_query_returns_results(chroma_client, mocker):
    _clear_vs_cache()
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import index_race_control_messages, query_race_control

    df = pd.DataFrame(
        {
            "message": ["Green flag start", "Red flag stopped", "Safety car on track"],
            "driver_number": [44, 1, 44],
            "category": ["Flag", "Flag", "Flag"],
            "flag": ["GREEN", "RED", "SAFETY_CAR"],
            "date": pd.to_datetime(["2025-03-16 12:00:00", "2025-03-16 12:05:00", "2025-03-16 12:10:00"]),
        }
    )
    index_race_control_messages(10014, df)

    results = query_race_control(10014, "safety car", n_results=3)
    assert len(results) > 0
    assert results[0]["message"] is not None
    assert results[0]["relevance"] >= 0.0
