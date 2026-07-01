import asyncio
import os
import threading
from collections.abc import Generator
from pathlib import Path
from typing import Any, Callable

import duckdb

_shared_conn: duckdb.DuckDBPyConnection | None = None
_shared_conn_lock = threading.Lock()


def _fact_pipeline_execution_schema() -> str:
    return """
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
        quarantine_rate DOUBLE,
        records_rejected INTEGER,
        data_freshness_minutes DOUBLE,
        sla_runtime_status VARCHAR,
        sla_quality_status VARCHAR,
        sla_freshness_status VARCHAR
    """


def _create_shared_connection() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:", read_only=False)

    parquet_glob = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../data/silver/fact_pipeline_execution/*/*.parquet",
        )
    )
    parquet_base = Path(parquet_glob.split("*")[0])

    if parquet_base.exists():
        try:
            conn.execute(
                f"CREATE OR REPLACE VIEW fact_pipeline_execution AS "
                f"SELECT * FROM read_parquet('{parquet_glob}')"
            )
            return conn
        except Exception:
            pass

    conn.execute(
        "CREATE OR REPLACE TABLE fact_pipeline_execution "
        f"({_fact_pipeline_execution_schema()})"
    )
    return conn


def _get_shared_connection() -> duckdb.DuckDBPyConnection:
    global _shared_conn
    if _shared_conn is None:
        with _shared_conn_lock:
            if _shared_conn is None:
                _shared_conn = _create_shared_connection()
    return _shared_conn


def close_shared_connection() -> None:
    global _shared_conn
    with _shared_conn_lock:
        if _shared_conn is not None:
            try:
                _shared_conn.close()
            except Exception:
                pass
            _shared_conn = None


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    yield _get_shared_connection()


async def run_query_async(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return await asyncio.to_thread(func, *args, **kwargs)
