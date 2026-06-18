"""
Health check endpoints for the OpenF1 Data Platform API.

Provides two distinct probes following Kubernetes/Docker conventions:
  - GET /health  → Liveness probe. Returns 200 if the process is alive.
  - GET /ready   → Readiness probe. Returns 200 only if the service can
    actually serve requests (DuckDB responsive, data files accessible).

Both endpoints are fast (<100ms target) and do not depend on the full
DuckDB view setup — they use a lightweight in-memory DuckDB for liveness
and check critical Parquet files for readiness.
"""

import os
import time
from typing import Any

import duckdb
from fastapi import APIRouter

router = APIRouter(prefix="/api")

# Critical data files that must exist for the service to be "ready"
# These are dimension tables queried on every request.
_REQUIRED_PARQUET_FILES = [
    "silver/dim_sessions.parquet",
    "silver/dim_drivers.parquet",
]


def _base_data_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))


def _check_duckdb_responsive() -> tuple[bool, str]:
    """Verify that DuckDB can run a trivial query."""
    try:
        conn = duckdb.connect(database=":memory:", read_only=False)
        conn.execute("SELECT 1")
        conn.close()
        return True, "duckdb_responsive"
    except Exception as e:
        return False, f"duckdb_unresponsive: {str(e)[:120]}"


def _check_required_files() -> list[dict[str, Any]]:
    """Check that critical Parquet files exist and are non-empty."""
    base = _base_data_dir()
    results = []
    for rel_path in _REQUIRED_PARQUET_FILES:
        full_path = os.path.join(base, rel_path)
        exists = os.path.exists(full_path)
        size = os.path.getsize(full_path) if exists else 0
        results.append(
            {
                "path": rel_path,
                "exists": exists,
                "size_bytes": size,
                "ok": exists and size > 0,
            }
        )
    return results


def _check_data_freshness() -> dict[str, Any]:
    """Return mtime-based freshness info for critical data dirs."""
    base = _base_data_dir()
    freshness: dict[str, Any] = {}
    for layer in ("bronze", "silver", "gold"):
        layer_path = os.path.join(base, layer)
        if not os.path.isdir(layer_path):
            freshness[layer] = {"exists": False, "age_minutes": None}
            continue

        latest_mtime = 0.0
        try:
            for dirpath, _, filenames in os.walk(layer_path):
                for fname in filenames:
                    if fname.endswith(".parquet"):
                        try:
                            mt = os.path.getmtime(os.path.join(dirpath, fname))
                            latest_mtime = max(latest_mtime, mt)
                        except OSError:
                            pass
        except OSError:
            pass

        if latest_mtime > 0:
            age_minutes = round((time.time() - latest_mtime) / 60, 1)
            freshness[layer] = {
                "exists": True,
                "age_minutes": age_minutes,
                "latest_file_epoch": int(latest_mtime),
            }
        else:
            freshness[layer] = {"exists": True, "age_minutes": None}

    return freshness


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Liveness probe. Returns 200 if the process is alive and DuckDB works.
    Lightweight — no filesystem I/O on the data directory.
    """
    ok, info = _check_duckdb_responsive()
    from fastapi import HTTPException

    if not ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "check": info},
        )
    return {"status": "healthy", "check": info}


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """
    Readiness probe. Returns 200 only if all critical files exist, DuckDB is
    responsive, and at least one data layer has data.
    """
    from fastapi import HTTPException

    checks: dict[str, Any] = {}

    # 1. DuckDB liveness
    ok, info = _check_duckdb_responsive()
    checks["duckdb"] = {"ok": ok, "detail": info}

    # 2. Required Parquet files
    file_checks = _check_required_files()
    files_ok = all(f["ok"] for f in file_checks)
    checks["required_files"] = {"ok": files_ok, "files": file_checks}

    # 3. Data freshness (for logging/alerting, not hard-failing)
    freshness = _check_data_freshness()
    checks["freshness"] = freshness

    # Aggregate readiness decision
    all_ok = all(checks[k]["ok"] for k in ("duckdb", "required_files"))

    if not all_ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks},
        )

    return {
        "status": "ready",
        "checks": checks,
        "timestamp_epoch": int(time.time()),
    }
