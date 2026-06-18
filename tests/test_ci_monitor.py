"""Tests for web/ci_monitor.py — CI monitoring and healing."""

import os
from unittest.mock import patch

from src.web.ci_monitor import ALERTS_DIR, get_latest_runs, get_run_jobs


def test_get_latest_runs_returns_list():
    with patch("src.web.ci_monitor.fetch_github_api") as mock_api:
        mock_api.return_value = {"workflow_runs": [{"id": 1, "conclusion": "success"}]}
        runs = get_latest_runs("owner/repo", "fake_token")
        assert len(runs) == 1
        assert runs[0]["conclusion"] == "success"


def test_get_latest_runs_empty_on_error():
    with patch("src.web.ci_monitor.fetch_github_api", side_effect=Exception("API error")):
        runs = get_latest_runs("owner/repo", "fake_token")
        assert runs == []


def test_get_run_jobs_returns_list():
    with patch("src.web.ci_monitor.fetch_github_api") as mock_api:
        mock_api.return_value = {"jobs": [{"id": 100, "status": "completed"}]}
        jobs = get_run_jobs("owner/repo", 1, "fake_token")
        assert len(jobs) == 1


def test_get_run_jobs_empty_on_error():
    with patch("src.web.ci_monitor.fetch_github_api", side_effect=Exception("timeout")):
        jobs = get_run_jobs("owner/repo", 1, "fake_token")
        assert jobs == []


def test_alerts_dir_exists():
    assert os.path.exists(ALERTS_DIR)
