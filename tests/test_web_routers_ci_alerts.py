import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.web.main import app


def test_trigger_ci_check_success():
    report = {"evaluated_run_id": 42, "status": "healed"}
    with patch("src.web.routers.ci_alerts.check_and_heal_ci", return_value=report):
        with TestClient(app) as c:
            resp = c.post("/api/ci/check?run_id=42")
    assert resp.status_code == 200
    assert resp.json()["evaluated_run_id"] == 42


def test_trigger_ci_check_no_run_id():
    report = {"evaluated_run_id": None, "status": "checked"}
    with patch("src.web.routers.ci_alerts.check_and_heal_ci", return_value=report):
        with TestClient(app) as c:
            resp = c.post("/api/ci/check")
    assert resp.status_code == 200


def test_trigger_ci_check_failure():
    with patch("src.web.routers.ci_alerts.check_and_heal_ci", side_effect=ValueError("API error")):
        with TestClient(app) as c:
            resp = c.post("/api/ci/check")
    assert resp.status_code == 500
    assert "API error" in resp.json()["detail"]


def test_get_ci_status_empty(tmp_path):
    from src.web.routers.ci_alerts import ALERTS_DIR

    with patch("src.web.routers.ci_alerts.ALERTS_DIR", str(tmp_path / "nonexistent")):
        with TestClient(app) as c:
            resp = c.get("/api/ci/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["history_count"] == 0
    assert data["history"] == []


def test_get_ci_status_with_reports(tmp_path):
    report_dir = tmp_path / "ci_reports"
    report_dir.mkdir()
    r1 = {"evaluated_run_id": 2, "status": "ok"}
    r2 = {"evaluated_run_id": 5, "status": "healed"}
    (report_dir / "ci_healing_report_2.json").write_text(json.dumps(r1))
    (report_dir / "ci_healing_report_5.json").write_text(json.dumps(r2))

    with patch("src.web.routers.ci_alerts.ALERTS_DIR", str(report_dir)):
        with TestClient(app) as c:
            resp = c.get("/api/ci/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["history_count"] == 2
    assert data["history"][0]["evaluated_run_id"] == 5
    assert data["history"][1]["evaluated_run_id"] == 2


def test_get_ci_status_skips_corrupted(tmp_path):
    report_dir = tmp_path / "ci_reports"
    report_dir.mkdir()
    (report_dir / "ci_healing_report_1.json").write_text("not valid json")

    with patch("src.web.routers.ci_alerts.ALERTS_DIR", str(report_dir)):
        with TestClient(app) as c:
            resp = c.get("/api/ci/status")
    assert resp.status_code == 200
    assert resp.json()["history_count"] == 0
