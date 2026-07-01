import json
import logging
import os
from datetime import datetime

from src.web.config import settings

ALERTS_DIR = os.path.join(settings.BASE_DIR, "data/alerts")
os.makedirs(ALERTS_DIR, exist_ok=True)

logger = logging.getLogger("ci_monitor")


def check_and_heal_ci(target_run_id: int = None) -> dict:
    return {
        "evaluated_run_id": target_run_id,
        "workflow_name": "manual-check",
        "status": "checked",
        "conclusion": "unknown",
        "checked_at": datetime.utcnow().isoformat(),
        "alert_triggered": False,
        "auto_healing_executed": False,
        "actions": [],
    }


def save_report(report: dict) -> str:
    run_id = report.get("evaluated_run_id", "manual")
    path = os.path.join(ALERTS_DIR, f"ci_healing_report_{run_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return path
