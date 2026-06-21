import logging
import os
import time
from datetime import datetime

import pandas as pd
from pydantic import ValidationError

from src.ingestion.storage import atomic_append_partitioned_file, atomic_write_dataframe

logger = logging.getLogger(__name__)


def calc_freshness_minutes(base_dir: str | None) -> float | None:
    if not base_dir or not os.path.isdir(base_dir):
        return None
    latest = 0.0
    for root, _dirs, files in os.walk(base_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(fp)
                latest = max(latest, mtime)
            except OSError:
                continue
    if latest == 0.0:
        return None
    return round((time.time() - latest) / 60.0, 2)


def write_session_partition(df: pd.DataFrame, target_dir: str) -> None:
    atomic_write_dataframe(df, os.path.join(target_dir, "data.parquet"))


def append_execution_record(part_exec_path: str, run_record: dict) -> None:
    atomic_append_partitioned_file(os.path.join(part_exec_path, "data.parquet"), pd.DataFrame([run_record]))


def quarantine_invalid_rows(df: pd.DataFrame, table_name: str, reason: str, partition_quarantine_dir: str):
    if df.empty:
        return
    os.makedirs(partition_quarantine_dir, exist_ok=True)
    df_quarantine = df.copy()
    df_quarantine["quarantine_timestamp"] = datetime.now()
    df_quarantine["quarantine_reason"] = reason
    quarantine_file = os.path.join(partition_quarantine_dir, f"{table_name}_corrupt.parquet")
    atomic_append_partitioned_file(quarantine_file, df_quarantine)
    logger.info("Quarantined %d rows of %s in %s by: %s", len(df), table_name, quarantine_file, reason)


def validate_pydantic_batch(df: pd.DataFrame, contract_cls, table_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    valid_rows = []
    invalid_rows = []
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        for k, v in row_dict.items():
            if isinstance(v, pd.Timestamp):
                row_dict[k] = v.to_pydatetime()
            elif pd.isna(v):
                row_dict[k] = None
        try:
            contract_cls(**row_dict)
            valid_rows.append(row_dict)
        except ValidationError as e:
            row_dict["error_detail"] = str(e)
            invalid_rows.append(row_dict)
    df_valid = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    df_invalid = pd.DataFrame(invalid_rows) if invalid_rows else pd.DataFrame()
    return df_valid, df_invalid


def validate_vectorized_batch(df: pd.DataFrame, schema: dict, required_cols: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    null_mask = df[required_cols].isna().any(axis=1)
    df_invalid_null = df[null_mask].copy()
    df_valid = df[~null_mask].copy()
    if not df_invalid_null.empty:
        df_invalid_null["error_detail"] = "Valor nulo em coluna mandatória de chave ou telemetria"
    df_invalid_types = pd.DataFrame()
    valid_rows = []
    for col, col_type in schema.items():
        if col in df_valid.columns:
            try:
                if col_type.startswith("datetime"):
                    df_valid[col] = pd.to_datetime(df_valid[col], format="ISO8601")
                elif col_type == "string":
                    df_valid[col] = df_valid[col].astype(str)
                else:
                    df_valid[col] = df_valid[col].astype(col_type)
            except Exception as e:
                logger.warning("Falha de cast da coluna %s para %s. Executando isolamento de linhas.", col, col_type)
                for idx, row in df_valid.iterrows():
                    try:
                        pd.Series([row[col]]).astype(col_type)
                        valid_rows.append(row.to_dict())
                    except Exception:
                        row_dict = row.to_dict()
                        row_dict["error_detail"] = "Falha de cast na coluna %s para %s: %s" % (col, col_type, e)
                        df_invalid_types = pd.concat(
                            [df_invalid_types, pd.DataFrame([row_dict])],
                            ignore_index=True,
                        )
                df_valid = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    df_invalid = (
        pd.concat([df_invalid_null, df_invalid_types], ignore_index=True)
        if not df_invalid_null.empty or not df_invalid_types.empty
        else pd.DataFrame()
    )
    return df_valid, df_invalid
