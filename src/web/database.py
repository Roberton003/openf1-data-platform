import asyncio
import os
import threading
import time
from functools import wraps
from typing import Any, Callable, Generator

import duckdb

# ---------------------------------------------------------------------------
# Empty-table schemas — used as stable fallbacks when Parquet data is absent.
# Keeping the view/contract alive prevents downstream code from crashing on
# missing tables.
# ---------------------------------------------------------------------------
EMPTY_TABLE_SCHEMAS = {
    "dim_sessions": """
        session_key INTEGER,
        year INTEGER,
        session_name VARCHAR,
        session_type VARCHAR,
        circuit_key INTEGER,
        circuit_short_name VARCHAR,
        country_name VARCHAR
    """,
    "dim_drivers": """
        driver_number INTEGER,
        full_name VARCHAR,
        name_acronym VARCHAR,
        team_name VARCHAR,
        country_code VARCHAR
    """,
    "dim_stints": """
        session_key INTEGER,
        driver_number INTEGER,
        stint_number INTEGER,
        compound VARCHAR,
        lap_start INTEGER,
        lap_end INTEGER,
        tyre_age_at_start INTEGER
    """,
    "dim_weather": """
        session_key INTEGER,
        date TIMESTAMP,
        air_temperature DOUBLE,
        track_temperature DOUBLE,
        humidity DOUBLE,
        wind_speed DOUBLE,
        rainfall INTEGER
    """,
    "fact_pit_stops": """
        session_key INTEGER,
        driver_number INTEGER,
        lap_number INTEGER,
        stop_duration DOUBLE,
        lane_duration DOUBLE,
        pit_duration DOUBLE,
        date TIMESTAMP
    """,
    "fact_race_control": """
        session_key INTEGER,
        driver_number INTEGER,
        category VARCHAR,
        flag VARCHAR,
        message VARCHAR,
        date TIMESTAMP
    """,
    "fact_intervals": """
        session_key INTEGER,
        driver_number INTEGER,
        gap_to_leader VARCHAR,
        interval VARCHAR,
        date TIMESTAMP
    """,
    "fact_session_results": """
        session_key INTEGER,
        driver_number INTEGER,
        position INTEGER,
        points DOUBLE,
        number_of_laps INTEGER
    """,
    "fact_overtakes": """
        session_key INTEGER,
        overtaking_driver_number INTEGER,
        overtaken_driver_number INTEGER,
        position INTEGER,
        date TIMESTAMP
    """,
    "fact_pipeline_execution": """
        run_id VARCHAR,
        pipeline_name VARCHAR,
        session_key INTEGER,
        execution_timestamp TIMESTAMP,
        duration_seconds DOUBLE,
        status VARCHAR,
        total_rows_processed INTEGER,
        total_rows_bronze INTEGER,
        total_rows_silver INTEGER,
        total_rows_quarantine INTEGER,
        quarantine_rate DOUBLE
    """,
    "fact_car_telemetry": """
        session_key INTEGER,
        driver_number INTEGER,
        date TIMESTAMP,
        x INTEGER,
        y INTEGER,
        z INTEGER,
        speed INTEGER,
        rpm INTEGER,
        n_gear INTEGER,
        throttle DOUBLE,
        brake DOUBLE,
        drs INTEGER
    """,
    "fact_car_location": """
        session_key INTEGER,
        driver_number INTEGER,
        date TIMESTAMP,
        x INTEGER,
        y INTEGER,
        z INTEGER
    """,
    "gold_features_lap_data": """
        session_key INTEGER,
        driver_number INTEGER,
        stint_number INTEGER,
        lap_number INTEGER,
        compound VARCHAR,
        compound_num DOUBLE,
        tyre_age_at_start INTEGER,
        max_speed DOUBLE,
        max_rpm DOUBLE,
        throttle_intensity_pct DOUBLE,
        brake_intensity_pct DOUBLE,
        lap_duration_seconds DOUBLE
    """,
    "gold_lap_predictions": """
        session_key INTEGER,
        driver_number INTEGER,
        stint_number INTEGER,
        lap_number INTEGER,
        compound VARCHAR,
        tyre_age_at_start INTEGER,
        lap_duration_seconds DOUBLE,
        predicted_lap_duration_seconds DOUBLE,
        delta_performance_seconds DOUBLE
    """,
    "fct_f1_telemetry_analysis": """
        session_key INTEGER,
        driver_number INTEGER,
        lap_number INTEGER,
        max_speed INTEGER,
        avg_speed DOUBLE,
        max_rpm INTEGER,
        avg_rpm DOUBLE,
        throttle_intensity_pct DOUBLE,
        brake_intensity_pct DOUBLE,
        drs_activation_pct DOUBLE,
        gear_changes INTEGER
    """,
}


def _create_empty_table(conn: duckdb.DuckDBPyConnection, table_name: str) -> None:
    schema = EMPTY_TABLE_SCHEMAS[table_name]
    conn.execute(f"CREATE OR REPLACE TABLE {table_name} ({schema})")


# ---------------------------------------------------------------------------
# Singleton DuckDB connection — per-instance, not per-request.
# ---------------------------------------------------------------------------
# Performance improvement (Sprint 4.3):
#   The original `get_db()` generator created a NEW in-memory DuckDB connection
#   and re-created all 14 views on every HTTP request. That was:
#     - ~14 DDL statements per request
#     - ~14 filesystem scans (any(os.scandir(...))) per request
#     - A scandir iterator leak (scandir wasn't closed on the fast path)
#
#   Now the same connection is reused across requests. The connection is
#   created lazily on first use, thread-safe via a lock, and properly closed
#   on shutdown via `close_shared_connection()`.
# ---------------------------------------------------------------------------
_shared_conn: duckdb.DuckDBPyConnection | None = None
_shared_conn_lock = threading.Lock()


def _has_parquet_files(directory: str) -> bool:
    """
    Check if a directory contains any Parquet files — safely closed scandir.
    Replaces the old `any(os.scandir(base_path))` which leaked ScandirIterator.
    """
    try:
        with os.scandir(directory) as it:
            return any(
                entry.is_file(follow_symlinks=False) and entry.name.endswith(".parquet")
                for entry in it
            )
    except OSError:
        return False


def _resolve_views_map() -> dict[str, str]:
    """
    Build the {view_name: file_pattern} map, resolved to absolute paths.
    Called once at connection setup time.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    silver_dir = os.path.join(base_dir, "silver")
    gold_dir = os.path.join(base_dir, "gold")

    return {
        "dim_sessions": os.path.join(silver_dir, "dim_sessions.parquet"),
        "dim_drivers": os.path.join(silver_dir, "dim_drivers.parquet"),
        "dim_stints": os.path.join(silver_dir, "dim_stints.parquet"),
        "dim_weather": os.path.join(silver_dir, "dim_weather.parquet"),
        "fact_pit_stops": os.path.join(silver_dir, "fact_pit_stops/*/*.parquet"),
        "fact_race_control": os.path.join(silver_dir, "fact_race_control/*/*.parquet"),
        "fact_intervals": os.path.join(silver_dir, "fact_intervals/*/*.parquet"),
        "fact_session_results": os.path.join(
            silver_dir, "fact_session_results/*/*.parquet"
        ),
        "fact_overtakes": os.path.join(silver_dir, "fact_overtakes/*/*.parquet"),
        "fact_pipeline_execution": os.path.join(
            silver_dir, "fact_pipeline_execution/*/*.parquet"
        ),
        "fact_car_telemetry": os.path.join(
            silver_dir, "fact_car_telemetry/*/*/*.parquet"
        ),
        "fact_car_location": os.path.join(
            silver_dir, "fact_car_location/*/*/*.parquet"
        ),
        "gold_features_lap_data": os.path.join(
            gold_dir, "features_lap_data/*/*.parquet"
        ),
        "gold_lap_predictions": os.path.join(gold_dir, "lap_predictions/*/*.parquet"),
        "fct_f1_telemetry_analysis": os.path.join(
            gold_dir, "fct_f1_telemetry_analysis.parquet"
        ),
    }


def _create_shared_connection() -> duckdb.DuckDBPyConnection:
    """
    Create and configure the shared DuckDB connection with views mapped to
    the Parquet lakehouse. Called once lazily via `_get_shared_connection()`.
    """
    conn = duckdb.connect(database=":memory:", read_only=False)

    views_map = _resolve_views_map()
    for table_name, file_pattern in views_map.items():
        try:
            if "*" in file_pattern:
                base_path = file_pattern.split("*")[0]
                if os.path.exists(base_path) and _has_parquet_files(base_path):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_parquet('{file_pattern}')"
                    )
                else:
                    _create_empty_table(conn, table_name)
            else:
                if os.path.exists(file_pattern):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_parquet('{file_pattern}')"
                    )
                else:
                    _create_empty_table(conn, table_name)
        except Exception:
            # Keep serving contracts stable when a dataset is absent or
            # has unreadable metadata.
            _create_empty_table(conn, table_name)

    # Performance tuning — use available cores but leave headroom.
    cpu_count = os.cpu_count() or 4
    threads = max(1, min(cpu_count - 1, 4))
    try:
        conn.execute(f"SET threads = {threads}")
    except Exception:
        pass

    return conn


def _get_shared_connection() -> duckdb.DuckDBPyConnection:
    """
    Get or create the shared DuckDB connection (thread-safe singleton).
    Lazy initialization on first call; reused across requests.
    """
    global _shared_conn
    if _shared_conn is None:
        with _shared_conn_lock:
            if _shared_conn is None:  # Double-checked locking
                _shared_conn = _create_shared_connection()
    return _shared_conn


def close_shared_connection() -> None:
    """
    Close the shared DuckDB connection. Called on FastAPI shutdown.
    Safe to call multiple times.
    """
    global _shared_conn
    with _shared_conn_lock:
        if _shared_conn is not None:
            try:
                _shared_conn.close()
            except Exception:
                pass
            _shared_conn = None


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    FastAPI dependency that yields the shared DuckDB connection.

    Performance note:
    This no longer creates a new connection per request. The shared connection
    is reused across all requests for the lifetime of the FastAPI process.
    For testing, override this dependency with a mock connection.
    """
    yield _get_shared_connection()


async def run_query_async(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Helper to run blocking DuckDB query execution on a worker thread using
    asyncio.to_thread. Prevents blocking the FastAPI main event loop.
    """
    return await asyncio.to_thread(func, *args, **kwargs)


# ---------------------------------------------------------------------------
# Simple TTL Cache — used to cache heavy analytical query results.
# ---------------------------------------------------------------------------
# Cache is keyed on (function_name, args, frozen_kwargs). The first argument
# (DuckDB connection) is EXCLUDED from the key so the same query cached
# across different request connections returns the same result.
#
# Default: 256 entries, 300-second (5 min) TTL.
# ---------------------------------------------------------------------------


class TTLCache:
    """Thread-safe in-memory TTL cache for analytical query results."""

    def __init__(self, maxsize: int = 256, ttl_seconds: float = 300.0) -> None:
        self._cache: dict[Any, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.maxsize = maxsize
        self.ttl = ttl_seconds

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Exclude the first arg (DuckDB connection) from the cache key.
            # This lets the cache survive across per-request connections.
            cache_key = self._make_key(func, args[1:] if args else (), kwargs)

            now = time.monotonic()
            with self._lock:
                entry = self._cache.get(cache_key)
                if entry is not None:
                    value, timestamp = entry
                    if now - timestamp < self.ttl:
                        return value
                    # Expired — remove
                    del self._cache[cache_key]

            # Cache miss — compute outside the lock
            result = func(*args, **kwargs)

            with self._lock:
                # Evict if over capacity (oldest entry by timestamp)
                if len(self._cache) >= self.maxsize:
                    oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]
                self._cache[cache_key] = (result, now)

            return result

        wrapper.cache_clear = lambda: self._clear()  # type: ignore[attr-defined]
        wrapper.cache_info = lambda: self._info()  # type: ignore[attr-defined]
        return wrapper

    @staticmethod
    def _make_key(func: Callable[..., Any], args: tuple, kwargs: dict) -> tuple:
        # Convert unhashable kwargs/dicts to a hashable tuple
        frozen_kwargs = tuple(sorted((k, _freeze(v)) for k, v in kwargs.items()))
        return (func.__module__, func.__qualname__, args, frozen_kwargs)

    def _clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def _info(self) -> dict[str, int]:
        with self._lock:
            return {"size": len(self._cache), "maxsize": self.maxsize}


def _freeze(value: Any) -> Any:
    """Make a value hashable for cache key construction."""
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, set, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


# Default shared cache instance used across the serving layer.
result_cache = TTLCache(maxsize=256, ttl_seconds=300)
