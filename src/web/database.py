import asyncio
from typing import Any, Callable, Generator

import duckdb

from src.web.config import settings


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Dependency generator yielding a read-only DuckDB connection per HTTP request.
    Ensures the connection is closed after the response is sent.
    """
    # Open connection in strict read-only mode to prevent locks and concurrency conflicts
    conn = duckdb.connect(database=settings.DATABASE_PATH, read_only=True)
    try:
        yield conn
    finally:
        conn.close()


async def run_query_async(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Helper to run blocking DuckDB query execution on a worker thread using asyncio.to_thread.
    Prevents blocking the FastAPI main event loop.
    """
    return await asyncio.to_thread(func, *args, **kwargs)
