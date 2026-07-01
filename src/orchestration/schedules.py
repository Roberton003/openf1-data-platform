"""
Schedules for Dagster orchestration.

Defines automated ingestion runs on a cron schedule.
"""

from dagster import AssetSelection, RunRequest, define_asset_job, schedule


@schedule(
    cron_schedule="0 6 * * *",
    target=define_asset_job("daily_ingestion", selection=AssetSelection.all()),
    execution_timezone="UTC",
)
def daily_ingestion_schedule(context):
    """Run daily at 06:00 UTC for all available GPs."""
    return RunRequest(
        run_key=None,
        run_config={
            "ops": {
                "extract": {
                    "config": {
                        "year": 2025,
                        "gp": "all",
                        "session": "Race",
                    }
                }
            }
        },
        tags={"source": "scheduler", "frequency": "daily"},
    )
