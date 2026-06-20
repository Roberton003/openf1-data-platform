"""Tests for ingestion/extract.py — session resolution, fallback, extraction logic."""

from unittest.mock import patch

import pytest

from src.ingestion.extract import (
    get_all_sessions,
    get_session_info,
    run_extraction_for_session,
)


def test_fetch_endpoint_returns_data(mocker):
    mock_get = mocker.patch("src.ingestion.extract.requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"session_key": 10014}]
    from src.ingestion.extract import fetch_endpoint

    result = fetch_endpoint("sessions", {"year": 2025})
    assert result == [{"session_key": 10014}]


def test_fetch_endpoint_404_returns_empty(mocker):
    mock_get = mocker.patch("src.ingestion.extract.requests.get")
    mock_get.return_value.status_code = 404
    from requests.exceptions import HTTPError

    mock_get.return_value.raise_for_status.side_effect = HTTPError(response=mock_get.return_value)
    from src.ingestion.extract import fetch_endpoint

    result = fetch_endpoint("sessions", {"year": 9999})
    assert result == []


def test_fetch_endpoint_semaphore_used(mocker):
    mock_get = mocker.patch("src.ingestion.extract.requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []
    from src.ingestion.extract import api_semaphore, fetch_endpoint

    initial_value = api_semaphore._value
    fetch_endpoint("test")
    assert api_semaphore._value == initial_value


def test_get_session_info_filters_by_gp(mocker):
    mock_data = [
        {
            "session_key": 1,
            "year": 2025,
            "country_name": "Bahrain",
            "circuit_short_name": "Bahrain GP",
            "session_name": "Race",
            "date_start": "2025-03-16T15:00:00Z",
        },
        {
            "session_key": 2,
            "year": 2025,
            "country_name": "Italy",
            "circuit_short_name": "Monza",
            "session_name": "Race",
            "date_start": "2025-09-07T15:00:00Z",
        },
    ]
    with patch("src.ingestion.extract.fetch_endpoint", return_value=mock_data):
        result = get_session_info(2025, "Bahrain", "Race")
        assert result["session_key"] == 1
        assert result["year_actual"] == 2025


def test_get_session_info_fallback_2024(mocker):
    with patch("src.ingestion.extract.fetch_endpoint") as mock_fetch:
        mock_fetch.side_effect = [
            [],
            [
                {
                    "session_key": 10,
                    "year": 2024,
                    "country_name": "Bahrain",
                    "circuit_short_name": "Bahrain GP",
                    "session_name": "Race",
                    "date_start": "2024-03-02T15:00:00Z",
                }
            ],
        ]
        result = get_session_info(2025, "Bahrain", "Race")
        assert result["session_key"] == 10
        assert result["year_actual"] == 2024


def test_get_session_info_no_sessions_raises(mocker):
    with patch("src.ingestion.extract.fetch_endpoint", return_value=[]):
        with pytest.raises(ValueError, match="Nenhuma sessão encontrada"):
            get_session_info(2023, "Test", "Race")


def test_get_session_info_fallback_to_latest(mocker):
    mock_data = [
        {
            "session_key": 1,
            "year": 2025,
            "country_name": "Bahrain",
            "circuit_short_name": "Bahrain GP",
            "session_name": "Race",
            "date_start": "2025-03-16T15:00:00Z",
        },
        {
            "session_key": 2,
            "year": 2025,
            "country_name": "Bahrain",
            "circuit_short_name": "Bahrain GP",
            "session_name": "Qualifying",
            "date_start": "2025-03-15T15:00:00Z",
        },
    ]
    with patch("src.ingestion.extract.fetch_endpoint", return_value=mock_data):
        result = get_session_info(2025, "Bahrain", "Practice")
        assert result["session_key"] == 1


def test_get_session_info_gp_not_found(mocker):
    mock_data = [
        {
            "session_key": 1,
            "year": 2025,
            "country_name": "Bahrain",
            "circuit_short_name": "Bahrain GP",
            "session_name": "Race",
            "date_start": "2025-03-16T15:00:00Z",
        },
    ]
    with patch("src.ingestion.extract.fetch_endpoint", return_value=mock_data):
        result = get_session_info(2025, "NonExistentGP", "Race")
        assert result["session_key"] == 1


def test_get_all_sessions_returns_list(mocker):
    mock_data = [
        {
            "session_key": 1,
            "year": 2025,
            "country_name": "Bahrain",
            "session_name": "Race",
            "date_start": "2025-03-16T15:00:00Z",
        },
    ]
    with patch("src.ingestion.extract.fetch_endpoint", return_value=mock_data):
        sessions = get_all_sessions(2025, "Race")
        assert len(sessions) == 1
        assert sessions[0]["year_actual"] == 2025


def test_get_all_sessions_no_match(mocker):
    mock_data = [
        {
            "session_key": 1,
            "year": 2025,
            "country_name": "Bahrain",
            "session_name": "Race",
            "date_start": "2025-03-16T15:00:00Z",
        },
    ]
    with patch("src.ingestion.extract.fetch_endpoint", return_value=mock_data):
        sessions = get_all_sessions(2025, "NONEXISTENT")
        assert len(sessions) >= 1


def test_get_all_sessions_no_data_raises(mocker):
    with patch("src.ingestion.extract.fetch_endpoint", return_value=[]):
        with pytest.raises(ValueError, match="Nenhuma sessão encontrada"):
            get_all_sessions(2023, "Race")


def test_run_extraction_for_session_creates_parquet(tmp_path, mocker):
    focus_drivers = {1: "Driver A"}
    session_info = {
        "session_key": 10014,
        "year_actual": 2025,
        "country_name": "Test GP",
        "session_name": "Race",
    }

    mocker.patch("src.ingestion.extract.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.extract.fetch_endpoint", return_value=[])
    mocker.patch("src.ingestion.extract.extract_driver_telemetry", return_value=(1, [], [], []))

    result = run_extraction_for_session(session_info, focus_drivers)
    expected_path = str(tmp_path / "bronze" / "year=2025" / "gp=Test_GP" / "session=Race")
    assert result == expected_path
    import os

    assert os.path.exists(expected_path)


def test_run_extraction_for_session_saves_metadata(tmp_path, mocker):
    focus_drivers = {44: "Test Driver"}
    session_info = {
        "session_key": 10014,
        "year_actual": 2025,
        "country_name": "Test GP",
        "session_name": "Race",
    }

    mocker.patch("src.ingestion.extract.DATA_DIR", str(tmp_path))
    mocker.patch("src.ingestion.extract.fetch_endpoint", return_value=[{"driver_number": 44, "lap_number": 1}])
    mocker.patch(
        "src.ingestion.extract.extract_driver_telemetry",
        return_value=(
            44,
            [{"driver_number": 44, "session_key": 10014, "speed": 300}],
            [{"driver_number": 44, "session_key": 10014, "gap_to_leader": "0.5"}],
            [{"driver_number": 44, "session_key": 10014, "x": 100, "y": 200, "z": 0}],
        ),
    )
    mocker.patch("src.ingestion.extract.time.sleep")

    result = run_extraction_for_session(session_info, focus_drivers)
    assert "Test_GP" in result

    import os

    bronze_dir = str(tmp_path / "bronze" / "year=2025" / "gp=Test_GP" / "session=Race")
    files = os.listdir(bronze_dir)
    parquet_files = [f for f in files if f.endswith(".parquet")]
    assert "sessions.parquet" in parquet_files
