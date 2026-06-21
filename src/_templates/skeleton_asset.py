"""Dagster asset template — < 50 line functions, typed, with error handling."""

import logging

import duckdb
import pandas as pd
from dagster import AssetExecutionContext, asset

logger = logging.getLogger(__name__)


@asset(
    compute_kind="duckdb",
    group_name="bronze",
    description="[description of what this asset produces]",
)
def asset_name(context: AssetExecutionContext) -> pd.DataFrame:
    """[One-line description].

    Args:
        context: Dagster execution context.

    Returns:
        DataFrame with schema: [col1, col2, ...]
    """
    try:
        con = duckdb.connect(database=":memory:")
        # replace with actual extraction logic
        df = con.execute("SELECT 1 AS col").fetchdf()
        result_count = len(df)
        context.log.info(f"asset_name: {result_count} rows")
        return df
    except duckdb.Error as e:
        logger.exception("asset_name failed: %s", e)
        context.log.error(f"asset_name failed: {e}")
        return pd.DataFrame()
