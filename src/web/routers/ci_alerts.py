import glob
import json
import os

from fastapi import APIRouter, HTTPException, Query

from src.web.ci_monitor import ALERTS_DIR, check_and_heal_ci

router = APIRouter(prefix="/api/ci", tags=["CI Monitor"])


@router.post("/check")
def trigger_ci_check(
    run_id: int = Query(None, description="Optional specific workflow run ID to verify")
):
    """Triggers an on-demand polling and auto-healing check for the CI/CD pipeline."""
    try:
        report = check_and_heal_ci(target_run_id=run_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CI check failed: {str(e)}")


@router.get("/status")
def get_ci_status():
    """Retrieves the history of all CI/CD evaluations and healing reports."""
    reports = []
    pattern = os.path.join(ALERTS_DIR, "ci_healing_report_*.json")

    for filepath in glob.glob(pattern):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reports.append(json.load(f))
        except Exception:
            # Silently skip corrupted reports to keep endpoint stable
            pass

    # Sort reports by run ID descending
    reports.sort(key=lambda x: x.get("evaluated_run_id", 0), reverse=True)

    return {
        "alerts_directory": ALERTS_DIR,
        "history_count": len(reports),
        "history": reports,
    }
