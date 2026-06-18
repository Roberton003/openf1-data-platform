"""
SLA endpoint — exposes pipeline execution SLAs with real metrics.
"""

import time
from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db

router = APIRouter(tags=["sla"])

GOLD_TABLES = [
    "fct_f1_telemetry_analysis",
    "gold_features_lap_data",
    "gold_lap_predictions",
]

GOLD_TABLE_PATHS = {
    "fct_f1_telemetry_analysis": "data/gold/fct_f1_telemetry_analysis.parquet",
    "gold_features_lap_data": "data/gold/features_lap_data",
    "gold_lap_predictions": "data/gold/lap_predictions",
}


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


def _calc_table_freshness(path_str: str) -> float | None:
    path = Path(path_str)
    if not path.exists():
        return None
    if path.is_file():
        return (time.time() - path.stat().st_mtime) / 60.0
    parquet_files = sorted(path.rglob("*.parquet"))
    if not parquet_files:
        return None
    latest_mtime = max(f.stat().st_mtime for f in parquet_files)
    return (time.time() - latest_mtime) / 60.0


@router.get("/api/pipeline_execution/sla/tables")
def get_table_sla():
    """Return SLA per gold table — freshness and availability."""
    results = []
    for table in GOLD_TABLES:
        rel_path = GOLD_TABLE_PATHS[table]
        freshness = _calc_table_freshness(rel_path)
        status = "COMPLIANT"
        if freshness is None:
            status = "NO_DATA"
        elif freshness > 60.0:
            status = "BREACHED"
        elif freshness > 30.0:
            status = "WARNING"

        results.append(
            {
                "table": table,
                "freshness_minutes": (
                    round(freshness, 2) if freshness is not None else None
                ),
                "status": status,
            }
        )

    total = len(results)
    breached = sum(1 for r in results if r["status"] == "BREACHED")
    no_data = sum(1 for r in results if r["status"] == "NO_DATA")

    return {
        "tables": results,
        "total_tables": total,
        "breached_count": breached,
        "no_data_count": no_data,
    }
