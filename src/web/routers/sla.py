"""
SLA endpoint — exposes pipeline execution SLAs with real metrics.
"""

from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db

router = APIRouter(tags=["sla"])


SLA_THRESHOLDS = {
    "runtime_seconds_max": 300.0,
    "quarantine_rate_max": 0.05,
    "freshness_minutes_max": 60.0,
}


def _compute_sla_status(row: dict[str, Any]) -> dict[str, str]:
    freshness = row.get("data_freshness_minutes")
    runtime_ok = row.get("duration_seconds", 0) <= SLA_THRESHOLDS["runtime_seconds_max"]
    quality_ok = row.get("quarantine_rate", 0) <= SLA_THRESHOLDS["quarantine_rate_max"]
    freshness_ok = (
        freshness is not None and freshness <= SLA_THRESHOLDS["freshness_minutes_max"]
    )
    return {
        "sla_runtime_status": "COMPLIANT" if runtime_ok else "BREACHED",
        "sla_quality_status": "COMPLIANT" if quality_ok else "BREACHED",
        "sla_freshness_status": "COMPLIANT" if freshness_ok else "BREACHED",
    }


@router.get("/api/pipeline_execution/sla")
def get_pipeline_sla(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Return SLA metrics for all pipeline executions."""
    try:
        rows = db.execute(
            "SELECT * FROM fact_pipeline_execution ORDER BY execution_timestamp DESC LIMIT 100"
        ).fetchall()
    except Exception:
        raise HTTPException(status_code=404, detail="No pipeline execution data found")

    if not rows:
        raise HTTPException(status_code=404, detail="No pipeline execution data found")

    columns = [desc[0] for desc in db.description]
    results = []
    for row in rows:
        record = dict(zip(columns, row))
        sla = _compute_sla_status(record)
        record.update(sla)
        results.append(record)

    total = len(results)
    breaches = sum(
        1
        for r in results
        if r["sla_runtime_status"] == "BREACHED"
        or r["sla_quality_status"] == "BREACHED"
        or r["sla_freshness_status"] == "BREACHED"
    )
    freshness = [
        r["data_freshness_minutes"]
        for r in results
        if r.get("data_freshness_minutes") is not None
    ]

    return {
        "total_executions": total,
        "breach_count": breaches,
        "breach_rate": round(breaches / total, 4) if total else 0.0,
        "avg_freshness_minutes": (
            round(sum(freshness) / len(freshness), 2) if freshness else None
        ),
        "executions": results,
    }
