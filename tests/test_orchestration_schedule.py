"""Tests for Dagster orchestration — schedule."""

from dagster import DagsterInstance, build_schedule_context

from src.orchestration.schedules import daily_ingestion_schedule


def test_schedule_name():
    assert daily_ingestion_schedule.name == "daily_ingestion_schedule"


def test_schedule_cron():
    assert daily_ingestion_schedule.cron_schedule == "0 6 * * *"


def test_schedule_timezone():
    assert daily_ingestion_schedule.execution_timezone == "UTC"


def test_schedule_run_config():
    context = build_schedule_context(instance=DagsterInstance.ephemeral())
    run_request = daily_ingestion_schedule(context)
    assert run_request.run_config["ops"]["extract"]["config"]["year"] == 2025
    assert run_request.run_config["ops"]["extract"]["config"]["gp"] == "all"
    assert run_request.run_config["ops"]["extract"]["config"]["session"] == "Race"


def test_schedule_tags():
    context = build_schedule_context(instance=DagsterInstance.ephemeral())
    run_request = daily_ingestion_schedule(context)
    assert run_request.tags["source"] == "scheduler"
    assert run_request.tags["frequency"] == "daily"


def test_schedule_registered_in_defs():
    from src.orchestration.definitions import defs
    names = [s.name for s in defs.schedules]
    assert "daily_ingestion_schedule" in names
