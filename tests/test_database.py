"""Tests for web/database.py — DuckDB connection, TTL cache, helpers."""

import threading

import duckdb
import pytest

from src.web.database import (
    EMPTY_TABLE_SCHEMAS,
    TTLCache,
    _create_empty_table,
    _freeze,
    _get_shared_connection,
    _has_parquet_files,
    _resolve_views_map,
    close_shared_connection,
    result_cache,
)


@pytest.fixture(autouse=True)
def _reset_shared_conn():
    close_shared_connection()
    yield
    close_shared_connection()


def test_has_parquet_files_true(tmp_path):
    parquet_file = tmp_path / "data.parquet"
    parquet_file.write_text("fake parquet")
    assert _has_parquet_files(str(tmp_path))


def test_has_parquet_files_false(tmp_path):
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("not parquet")
    assert not _has_parquet_files(str(tmp_path))


def test_has_parquet_files_empty_dir(tmp_path):
    assert not _has_parquet_files(str(tmp_path))


def test_has_parquet_files_nonexistent_dir():
    assert not _has_parquet_files("/nonexistent/path")


def test_create_empty_table():
    conn = duckdb.connect(":memory:")
    _create_empty_table(conn, "dim_sessions")
    result = conn.execute("SELECT * FROM dim_sessions").fetchall()
    assert result == []


def test_resolve_views_map_returns_dict():
    views = _resolve_views_map()
    assert "dim_sessions" in views
    assert "fact_car_telemetry" in views
    assert "gold_lap_predictions" in views
    assert isinstance(views["dim_sessions"], str)
    assert views["dim_sessions"].endswith("dim_sessions.parquet")


def test_get_shared_connection_singleton():
    conn1 = _get_shared_connection()
    conn2 = _get_shared_connection()
    assert conn1 is conn2


def test_get_shared_connection_thread_safe():
    connections = []

    def get_conn():
        connections.append(_get_shared_connection())

    threads = [threading.Thread(target=get_conn) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(c is connections[0] for c in connections)


def test_close_shared_connection():
    conn = _get_shared_connection()
    assert conn is not None
    close_shared_connection()
    new_conn = _get_shared_connection()
    assert new_conn is not conn


def test_close_shared_connection_idempotent():
    close_shared_connection()
    close_shared_connection()


def test_shared_connection_has_views():
    conn = _get_shared_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    table_names = {t[0] for t in tables}
    assert "dim_sessions" in table_names
    assert "dim_drivers" in table_names


def test_shared_connection_views_exist():
    conn = _get_shared_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    table_names = {t[0] for t in tables}
    assert "dim_sessions" in table_names
    assert "dim_drivers" in table_names


def test_create_empty_table_all_schemas():
    conn = duckdb.connect(":memory:")
    for table_name in EMPTY_TABLE_SCHEMAS:
        _create_empty_table(conn, table_name)
    for table_name in EMPTY_TABLE_SCHEMAS:
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        assert rows == [], f"{table_name} should be empty"


def test_freeze_dict():
    result = _freeze({"b": 2, "a": 1})
    assert result == (("a", 1), ("b", 2))


def test_freeze_list():
    result = _freeze([3, 1, 2])
    assert result == (3, 1, 2)


def test_freeze_set():
    result = _freeze({3, 1, 2})
    assert isinstance(result, tuple)
    assert sorted(result) == [1, 2, 3]


def test_freeze_nested():
    result = _freeze({"key": [3, 1, 2], "nested": {"a": 1}})
    assert result == (("key", (3, 1, 2)), ("nested", (("a", 1),)))


def test_freeze_plain_value():
    assert _freeze(42) == 42
    assert _freeze("hello") == "hello"


def test_result_cache_is_ttlcache():
    assert isinstance(result_cache, TTLCache)


def test_ttlcache_expiration():
    cache = TTLCache(maxsize=10, ttl_seconds=0)
    call_count = 0

    @cache
    def func(conn, x):
        nonlocal call_count
        call_count += 1
        return x

    func("c", 1)
    assert call_count == 1
    func("c", 1)
    assert call_count == 2


def test_ttlcache_clear():
    cache = TTLCache(maxsize=10, ttl_seconds=60)
    call_count = 0

    @cache
    def func(conn, x):
        nonlocal call_count
        call_count += 1
        return x

    func("c", 1)
    assert call_count == 1
    func.cache_clear()
    func("c", 1)
    assert call_count == 2


def test_ttlcache_info():
    cache = TTLCache(maxsize=10, ttl_seconds=60)

    @cache
    def func(conn, x):
        return x

    info = func.cache_info()
    assert info["maxsize"] == 10
    assert info["size"] == 0

    func("c", 1)
    info = func.cache_info()
    assert info["size"] == 1


def test_ttlcache_eviction_oldest():
    cache = TTLCache(maxsize=2, ttl_seconds=60)
    call_count = 0

    @cache
    def func(conn, x):
        nonlocal call_count
        call_count += 1
        return x

    func("c", 1)
    func("c", 2)
    func("c", 3)
    func("c", 1)
    assert call_count == 4
