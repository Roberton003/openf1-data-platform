"""Tests for SQL validation in web/routers/analytics.py."""

import pytest
from fastapi import HTTPException

from src.web.routers.analytics import _validate_and_prepare_sql


def test_valid_select():
    result = _validate_and_prepare_sql("SELECT * FROM dim_sessions")
    assert "SELECT" in result.upper()


def test_valid_with_cte():
    result = _validate_and_prepare_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")
    assert "WITH" in result.upper()


def test_empty_query_raises():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("")
    assert exc_info.value.status_code == 400


def test_insert_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("INSERT INTO dim_sessions VALUES (1)")
    assert exc_info.value.status_code in (400, 403)


def test_delete_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("DELETE FROM dim_sessions WHERE session_key = 1")
    assert exc_info.value.status_code in (400, 403)


def test_drop_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("DROP TABLE dim_sessions")
    assert exc_info.value.status_code in (400, 403)


def test_update_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("UPDATE dim_sessions SET year = 2026")
    assert exc_info.value.status_code in (400, 403)


def test_create_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("CREATE TABLE evil (id INT)")
    assert exc_info.value.status_code in (400, 403)


def test_truncate_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("TRUNCATE TABLE dim_sessions")
    assert exc_info.value.status_code in (400, 403)


def test_limit_injected_when_absent():
    result = _validate_and_prepare_sql("SELECT * FROM dim_sessions")
    assert "LIMIT" in result.upper()


def test_limit_not_duplicated_when_present():
    result = _validate_and_prepare_sql("SELECT * FROM dim_sessions LIMIT 10")
    count = result.upper().count("LIMIT")
    assert count == 1


def test_select_with_comment_allowed():
    result = _validate_and_prepare_sql("SELECT 1; -- DROP TABLE dim_sessions")
    assert "SELECT" in result.upper()


def test_write_parquet_blocked():
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_sql("SELECT write_parquet('out.parquet')")
    assert exc_info.value.status_code in (400, 403)
