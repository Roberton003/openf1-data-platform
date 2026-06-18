"""Tests for web/ci_monitor.py — additional functions for coverage."""

import json
import os
from unittest.mock import MagicMock, patch

from src.web.ci_monitor import (
    execute_healing_action,
    notify_local,
    send_alert_email,
    ALERTS_DIR,
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
