import os
import time
import pandas as pd
from src.ingestion.storage import atomic_append_partitioned_file, atomic_write_dataframe


def calc_freshness_minutes(base_dir: str | None) -> float | None:
    if not base_dir or not os.path.isdir(base_dir):
        return None
    latest = 0.0
    for root, _dirs, files in os.walk(base_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(fp)
                if mtime > latest:
                    latest = mtime
            except OSError:
                continue
    if latest == 0.0:
        return None
    return round((time.time() - latest) / 60.0, 2)


def write_session_partition(df: pd.DataFrame, target_dir: str) -> None:
    atomic_write_dataframe(df, os.path.join(target_dir, "data.parquet"))


def append_execution_record(part_exec_path: str, run_record: dict) -> None:
    atomic_append_partitioned_file(os.path.join(part_exec_path, "data.parquet"), pd.DataFrame([run_record]))
