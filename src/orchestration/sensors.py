"""
Sensors for Dagster orchestration.

Detects stale Bronze data and triggers reprocessing.
"""

import os
from datetime import UTC, datetime

from dagster import RunRequest, sensor

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))


@sensor(
    job_name="daily_ingestion",
    minimum_interval_seconds=3600,
)
def freshness_sensor(context):
    """Check if Bronze data is stale (>24h) and trigger fresh ingestion."""
    bronze_dir = os.path.join(DATA_DIR, "bronze")
    if not os.path.isdir(bronze_dir):
        context.log.info("Bronze directory missing, triggering ingestion")
        yield RunRequest(
            run_key=f"freshness_{datetime.now(UTC).isoformat()}",
            tags={"source": "sensor", "trigger": "missing_bronze"},
        )
        return

    latest_mtime = 0.0
    for root, _dirs, files in os.walk(bronze_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(fp)
                if mtime > latest_mtime:
                    latest_mtime = mtime
            except OSError:
                continue

    if latest_mtime == 0.0:
        return

    age_hours = (datetime.now(UTC).timestamp() - latest_mtime) / 3600
    context.log.info(f"Bronze oldest data age: {age_hours:.1f}h")

    if age_hours > 24:
        yield RunRequest(
            run_key=f"stale_{datetime.now(UTC).isoformat()}",
            tags={
                "source": "sensor",
                "trigger": "stale_data",
                "age_hours": str(round(age_hours, 1)),
            },
        )
