"""
Dagster Orchestration Module

This module isolates Dagster definitions (assets, jobs, schedules) from the
ingestion logic. This separation improves:
- Testability: ingestion logic can be tested without Dagster dependencies
- Maintainability: orchestration concerns are separate from data processing
- Clarity: clear boundary between "what to do" and "when to do it"

Usage:
    from src.orchestration.definitions import defs

    # Or run with:
    dagster dev -m src.orchestration.definitions
"""

from dagster import Definitions, load_assets_from_modules

from src.ingestion import assets
from src.orchestration.schedules import daily_ingestion_schedule
from src.orchestration.sensors import freshness_sensor

# Load all assets from the ingestion module
all_assets = load_assets_from_modules([assets])

# Define the Dagster repository
defs = Definitions(
    assets=all_assets,
    schedules=[daily_ingestion_schedule],
    sensors=[freshness_sensor],
)
