import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.web import ci_monitor
from src.web.config import settings


@pytest.fixture(autouse=True)
def clean_alerts_dir():
    """Ensures test alerts do not pollute or conflict with real ones."""
    # Create dir if not exists
    os.makedirs(ci_monitor.ALERTS_DIR, exist_ok=True)
    yield
    # We don't delete files as they are useful for local state, but we ensure it works safely


@patch("src.web.ci_monitor.requests.get")
def test_fetch_github_api_success(mock_get):
    """Verifies that API helper adds token, User-Agent, and returns json data."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    result = ci_monitor.fetch_github_api("https://api.github.com/test", token="xyz")

    assert result == {"status": "ok"}
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer xyz"
    assert kwargs["headers"]["User-Agent"] == "OpenF1-CI-Monitor"


@patch("src.web.ci_monitor.fetch_github_api")
def test_get_latest_runs(mock_fetch):
    """Verifies retrieval of action runs list from the API response."""
    mock_fetch.return_value = {
        "workflow_runs": [{"id": 123, "status": "completed", "conclusion": "success"}]
    }

    runs = ci_monitor.get_latest_runs("test-owner/test-repo", token="abc")
    assert len(runs) == 1
    assert runs[0]["id"] == 123
    mock_fetch.assert_called_once_with(
        "https://api.github.com/repos/test-owner/test-repo/actions/runs", "abc"
    )


@patch("src.web.ci_monitor.fetch_github_api")
@patch("src.web.ci_monitor.subprocess.run")
@patch("src.web.ci_monitor.send_alert_email")
def test_check_and_heal_ci_success(mock_email, mock_sub, mock_fetch, monkeypatch):
    """If the pipeline passed successfully, no alerts or auto-healing actions should trigger."""
    monkeypatch.setattr(settings, "GITHUB_REPO", "owner/repo")

    # Mock latest run to be successful
    mock_fetch.return_value = {
        "workflow_runs": [
            {
                "id": 999,
                "name": "CI Pipeline",
                "status": "completed",
                "conclusion": "success",
                "head_sha": "sha123",
            }
        ]
    }

    report = ci_monitor.check_and_heal_ci()

    assert report["evaluated_run_id"] == 999
    assert report["conclusion"] == "success"
    assert report["alert_triggered"] is False
    assert report["auto_healing_executed"] is False
    mock_email.assert_not_called()
    mock_sub.assert_not_called()


@patch("src.web.ci_monitor.fetch_github_api")
@patch("src.web.ci_monitor.subprocess.run")
@patch("src.web.ci_monitor.send_alert_email")
def test_check_and_heal_ci_failure_triggers_healing(
    mock_email, mock_sub, mock_fetch, monkeypatch
):
    """If the pipeline failed, alerts should be sent and auto-healing should execute."""
    monkeypatch.setattr(settings, "GITHUB_REPO", "owner/repo")
    monkeypatch.setattr(settings, "AUTO_HEAL_CI", True)

    # Mock workflow run list (failure run)
    runs_mock = {
        "workflow_runs": [
            {
                "id": 888,
                "name": "CI Pipeline",
                "status": "completed",
                "conclusion": "failure",
                "head_sha": "sha_fail",
            }
        ]
    }
    # Mock jobs list containing steps
    jobs_mock = {
        "jobs": [
            {
                "name": "lint-and-test",
                "steps": [
                    {"name": "Code Formatting Check (Black)", "conclusion": "failure"},
                    {
                        "name": "Static Analysis & Lint (Flake8)",
                        "conclusion": "success",
                    },
                    {
                        "name": "Run Unit & Integration Tests (Pytest)",
                        "conclusion": "success",
                    },
                ],
            }
        ]
    }

    # Setup fetch side_effects for runs and then jobs
    mock_fetch.side_effect = [runs_mock, jobs_mock]

    # Mock subprocess runs (make format should run because black failed)
    mock_sub_res = MagicMock()
    mock_sub_res.return_code = 0
    mock_sub_res.stdout = "Formatting fixed"
    mock_sub_res.stderr = ""
    mock_sub.return_value = mock_sub_res

    report = ci_monitor.check_and_heal_ci(target_run_id=888)

    assert report["evaluated_run_id"] == 888
    assert report["conclusion"] == "failure"
    assert report["alert_triggered"] is True
    assert report["auto_healing_executed"] is True

    # Verify email alert triggered
    mock_email.assert_called_once_with(
        888, "CI Pipeline", "failure", "sha_fail", ["Code Formatting Check (Black)"]
    )

    # Verify subprocess calls (first is notify-send, second is make format)
    assert mock_sub.call_count == 2
    assert mock_sub.call_args_list[0][0][0][0] == "notify-send"
    assert mock_sub.call_args_list[1][0][0] == ["make", "format"]

    # Verify report was written to file
    report_file = os.path.join(ci_monitor.ALERTS_DIR, "ci_healing_report_888.json")
    assert os.path.exists(report_file)
    with open(report_file, "r") as f:
        saved_report = json.load(f)
        assert saved_report["evaluated_run_id"] == 888
        assert saved_report["alert_triggered"] is True
        assert saved_report["auto_healing_executed"] is True


def test_send_alert_email_mock_fallback(monkeypatch):
    """Verifies that if SMTP server configurations are empty, email is skipped safely."""
    # Ensure SMTP settings are empty
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "ALERT_EMAIL_RECEIVER", "")

    result = ci_monitor.send_alert_email(
        run_id=555,
        workflow_name="CI Test",
        conclusion="timed_out",
        commit_sha="abcdef",
        failed_steps=["pytest"],
    )

    assert result["sent"] is False
    assert result["mode"] == "MOCK"
    assert result["file_path"] is None
