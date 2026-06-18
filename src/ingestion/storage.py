from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import pandas as pd


def atomic_write_dataframe(df: pd.DataFrame, target_file: str) -> None:
    """Write a Parquet file atomically in the same filesystem."""
    target_path = Path(target_file)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f"{target_path.name}.tmp-{uuid.uuid4().hex}")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, target_path)


def atomic_write_partitioned_parquet(df: pd.DataFrame, target_dir: str, partition_cols: list[str]) -> None:
    """Write a partitioned Parquet dataset atomically by directory replacement."""
    target_path = Path(target_dir)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = target_path.with_name(f"{target_path.name}.__tmp__{uuid.uuid4().hex}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(tmp_dir, index=False, partition_cols=partition_cols)
    if target_path.exists():
        shutil.rmtree(target_path, ignore_errors=True)
    shutil.move(str(tmp_dir), str(target_path))


def atomic_append_partitioned_file(partition_file: str, new_rows: pd.DataFrame) -> None:
    """Append rows to a single Parquet file, preserving atomic replacement."""
    target_path = Path(partition_file)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        try:
            existing_df = pd.read_parquet(target_path)
            merged = pd.concat([existing_df, new_rows], ignore_index=True)
        except Exception:
            merged = new_rows
    else:
        merged = new_rows
    atomic_write_dataframe(merged, str(target_path))
