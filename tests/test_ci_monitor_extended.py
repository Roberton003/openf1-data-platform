"""Tests for web/ci_monitor.py — additional functions for coverage."""

import os
from unittest.mock import MagicMock, patch

from src.web.ci_monitor import (
    ALERTS_DIR,
    execute_healing_action,
    notify_local,
    send_alert_email,
)


def test_notify_local_with_notify_send():
    with patch("src.web.ci_monitor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        notify_local("test-workflow", "failure", 123)
        mock_run.assert_called_once()


def test_notify_local_fallback_on_error():
    with patch("src.web.ci_monitor.subprocess.run", side_effect=Exception("no display")):
        notify_local("test-workflow", "failure", 123)


def test_send_alert_email_no_smtp():
    with patch("src.web.ci_monitor.settings") as mock_settings:
        mock_settings.SMTP_HOST = None
        mock_settings.SMTP_USER = None
        mock_settings.SMTP_PASSWORD = None
        mock_settings.ALERT_EMAIL_RECEIVER = None
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_FROM = None
        result = send_alert_email(123, "test", "failure", "abc123", ["step1"])
        assert result["sent"] is False
        assert result["mode"] == "MOCK"


def test_execute_healing_action_format_fail():
    with patch("src.web.ci_monitor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        actions = execute_healing_action(["black check failed"], 123)
        assert len(actions) > 0
        assert actions[0]["action"] == "make format"


def test_execute_healing_action_lint_fail():
    with patch("src.web.ci_monitor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        actions = execute_healing_action(["flake8 lint failed"], 123)
        assert len(actions) > 0


def test_execute_healing_action_test_fail():
    with patch("src.web.ci_monitor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fail")
        actions = execute_healing_action(["pytest failed"], 123)
        assert len(actions) > 0


def test_execute_healing_action_empty_steps():
    with patch("src.web.ci_monitor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        actions = execute_healing_action([], 123)
        assert len(actions) > 0


def test_alerts_dir_exists():
    assert os.path.exists(ALERTS_DIR)


def test_send_alert_email_returns_dict():
    with patch("src.web.ci_monitor.settings") as mock_settings:
        mock_settings.SMTP_HOST = None
        mock_settings.SMTP_USER = None
        mock_settings.SMTP_PASSWORD = None
        mock_settings.ALERT_EMAIL_RECEIVER = None
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_FROM = None
        result = send_alert_email(456, "workflow", "failure", "sha", [])
        assert isinstance(result, dict)
        assert "sent" in result
        assert "mode" in result


def test_fetch_github_api_with_token():
    with patch("src.web.ci_monitor.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": "ok"}
        from src.web.ci_monitor import fetch_github_api

        result = fetch_github_api("https://api.github.com/test", "ghp_fake")
        assert result == {"data": "ok"}
        auth_header = mock_get.call_args[1]["headers"]["Authorization"]
        assert "ghp_fake" in auth_header


def test_fetch_github_api_without_token():
    with patch("src.web.ci_monitor.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": "ok"}
        from src.web.ci_monitor import fetch_github_api

        result = fetch_github_api("https://api.github.com/test", "")
        assert result == {"data": "ok"}
        assert "Authorization" not in mock_get.call_args[1]["headers"]


def test_fetch_github_api_http_error():
    with patch("src.web.ci_monitor.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP 500")
        import pytest

        from src.web.ci_monitor import fetch_github_api

        with pytest.raises(Exception, match="HTTP 500"):
            fetch_github_api("https://api.github.com/test")


def test_send_alert_email_smtp_success():
    with (
        patch("src.web.ci_monitor.settings") as mock_settings,
        patch("src.web.ci_monitor.smtplib.SMTP") as mock_smtp,
    ):
        mock_settings.SMTP_HOST = "smtp.test.com"
        mock_settings.SMTP_USER = "user@test.com"
        mock_settings.SMTP_PASSWORD = "secret"  # pragma: allowlist secret
        mock_settings.ALERT_EMAIL_RECEIVER = "alert@test.com"
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_FROM = "from@test.com"
        mock_smtp.return_value.__enter__.return_value = mock_smtp.return_value
        result = send_alert_email(123, "wf", "failure", "sha1", ["step1"])
        assert result["sent"] is True
        assert result["mode"] == "SMTP"


def test_send_alert_email_smtp_failure_fallback():
    with (
        patch("src.web.ci_monitor.settings") as mock_settings,
        patch("src.web.ci_monitor.smtplib.SMTP") as mock_smtp,
    ):
        mock_settings.SMTP_HOST = "smtp.test.com"
        mock_settings.SMTP_USER = "user@test.com"
        mock_settings.SMTP_PASSWORD = "secret"  # pragma: allowlist secret
        mock_settings.ALERT_EMAIL_RECEIVER = "alert@test.com"
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_FROM = "from@test.com"
        mock_smtp.side_effect = Exception("SMTP connection refused")
        result = send_alert_email(123, "wf", "failure", "sha1", ["step1"])
        assert result["sent"] is False
        assert result["mode"] == "MOCK_FALLBACK"


def test_execute_healing_action_format_error():
    with patch("src.web.ci_monitor.subprocess.run", side_effect=Exception("subprocess failed")):
        actions = execute_healing_action(["black failed"], 123)
        assert len(actions) >= 1
        assert actions[0]["status"] == "error"


def test_execute_healing_action_lint_error():
    with (
        patch("src.web.ci_monitor.subprocess.run", side_effect=Exception("subprocess failed")),
        patch("builtins.open", side_effect=Exception("write failed")),
    ):
        actions = execute_healing_action(["flake8 lint failed"], 123)
        assert actions[0]["status"] == "error"


def test_execute_healing_action_test_error():
    with patch("src.web.ci_monitor.subprocess.run", side_effect=Exception("subprocess failed")):
        actions = execute_healing_action(["pytest failed"], 123)
        assert actions[0]["status"] == "error"


def test_check_and_heal_ci_no_runs():
    with patch("src.web.ci_monitor.settings") as mock_settings:
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.GITHUB_TOKEN = None
        mock_settings.AUTO_HEAL_CI = False
        with patch("src.web.ci_monitor.get_latest_runs", return_value=[]):
            from src.web.ci_monitor import check_and_heal_ci

            result = check_and_heal_ci()
            assert result["status"] == "error"


def test_check_and_heal_ci_success_no_alert():
    with patch("src.web.ci_monitor.settings") as mock_settings:
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.GITHUB_TOKEN = None
        mock_settings.AUTO_HEAL_CI = False
        mock_settings.ALERT_EMAIL_RECEIVER = None
        with patch(
            "src.web.ci_monitor.get_latest_runs",
            return_value=[{"id": 1, "name": "CI", "status": "completed", "conclusion": "success", "head_sha": "abc"}],
        ):
            from src.web.ci_monitor import check_and_heal_ci

            result = check_and_heal_ci()
            assert result["alert_triggered"] is False
            assert result["conclusion"] == "success"


def test_check_and_heal_ci_failure_with_healing():
    with patch("src.web.ci_monitor.settings") as mock_settings:
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.GITHUB_TOKEN = None
        mock_settings.AUTO_HEAL_CI = True
        mock_settings.ALERT_EMAIL_RECEIVER = None
        mock_settings.SMTP_HOST = None
        mock_settings.SMTP_USER = None
        mock_settings.SMTP_PASSWORD = None
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_FROM = None
        with (
            patch(
                "src.web.ci_monitor.get_latest_runs",
                return_value=[
                    {"id": 42, "name": "CI", "status": "completed", "conclusion": "failure", "head_sha": "def"}
                ],
            ),
            patch(
                "src.web.ci_monitor.get_run_jobs", return_value=[{"steps": [{"name": "test", "conclusion": "failure"}]}]
            ),
            patch("src.web.ci_monitor.notify_local"),
            patch(
                "src.web.ci_monitor.execute_healing_action", return_value=[{"action": "make test", "status": "logged"}]
            ),
            patch("src.web.ci_monitor.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            from src.web.ci_monitor import check_and_heal_ci

            result = check_and_heal_ci()
            assert result["alert_triggered"] is True
            assert result["auto_healing_executed"] is True


def test_check_and_heal_ci_target_run_not_found():
    with patch("src.web.ci_monitor.settings") as mock_settings:
        mock_settings.GITHUB_REPO = "test/repo"
        mock_settings.GITHUB_TOKEN = None
        mock_settings.AUTO_HEAL_CI = False
        mock_settings.ALERT_EMAIL_RECEIVER = None
        with patch(
            "src.web.ci_monitor.get_latest_runs",
            return_value=[{"id": 1, "name": "CI", "status": "completed", "conclusion": "success", "head_sha": "abc"}],
        ):
            from src.web.ci_monitor import check_and_heal_ci

            result = check_and_heal_ci(target_run_id=999)
            assert result["evaluated_run_id"] == 1
