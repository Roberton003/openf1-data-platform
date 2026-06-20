"""Tests for ingestion/assets.py — fetch_api with retry and error handling."""

import requests

from src.ingestion.assets import fetch_api, SESSIONS_TO_PROCESS


class MockResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or []

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self, request=None)


def test_fetch_api_returns_json(mocker):
    mock_get = mocker.patch("src.ingestion.assets.requests.get")
    mock_get.return_value = MockResponse(200, [{"session_key": 10014, "year": 2025}])
    result = fetch_api("sessions", {"session_key": 10014})
    assert len(result) == 1
    assert result[0]["session_key"] == 10014


def test_fetch_api_404_returns_empty(mocker):
    mock_get = mocker.patch("src.ingestion.assets.requests.get")
    mock_get.return_value = MockResponse(404)
    result = fetch_api("sessions", {"session_key": 99999})
    assert result == []


def test_fetch_api_params_passed_correctly(mocker):
    mock_get = mocker.patch("src.ingestion.assets.requests.get")
    mock_get.return_value = MockResponse()
    fetch_api("sessions", {"session_key": 10014, "year": 2025})
    args, kwargs = mock_get.call_args
    assert "sessions" in args[0]
    assert kwargs["params"]["session_key"] == 10014


def test_sessions_to_process_structure():
    for s in SESSIONS_TO_PROCESS:
        assert "year" in s
        assert "session_key" in s
        assert "gp" in s
        assert isinstance(s["session_key"], int)
