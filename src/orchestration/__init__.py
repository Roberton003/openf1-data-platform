"""
Orchestration module for Dagster definitions.

This module isolates Dagster orchestration logic from ingestion logic.
"""

from src.orchestration.definitions import defs

__all__ = ["defs"]
