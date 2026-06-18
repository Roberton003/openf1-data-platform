"""
Tests for the ChromaDB-backed vector store.
"""

import pandas as pd
import pytest


@pytest.mark.slow
def test_index_and_query_race_control(chroma_client, mocker):
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
    mocker.patch("src.ingestion.vector_store.get_chroma_client", return_value=chroma_client)
    from src.ingestion.vector_store import get_race_control_collection, index_race_control_messages

    df_empty = pd.DataFrame()
    index_race_control_messages(10014, df_empty)
    collection = get_race_control_collection()
    assert collection.count() == 0


def test_query_returns_results(chroma_client, mocker):
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
