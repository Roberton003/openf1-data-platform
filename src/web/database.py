import asyncio
import os
from typing import Any, Callable, Generator

import duckdb


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Dependency generator yielding an in-memory DuckDB connection mapped to Parquet datasets.
    Provides serverless query engine capability with zero write locks.
    """
    conn = duckdb.connect(database=":memory:", read_only=False)

    # Resolvendo caminhos absolutos do Data Lakehouse
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    silver_dir = os.path.join(base_dir, "silver")
    gold_dir = os.path.join(base_dir, "gold")

    # Mapeamento de Views Temporárias sobre os arquivos Parquet físicos
    views_map = {
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
        # Tabelas Fatos Particionadas por driver
        "fact_car_telemetry": os.path.join(
            silver_dir, "fact_car_telemetry/*/*/*.parquet"
        ),
        "fact_car_location": os.path.join(
            silver_dir, "fact_car_location/*/*/*.parquet"
        ),
        # Camada Gold (Predições da IA)
        "gold_lap_predictions": os.path.join(gold_dir, "lap_predictions.parquet"),
    }

    for table_name, file_pattern in views_map.items():
        try:
            if "*" in file_pattern:
                # Se for caminho de busca globlal particionado, checa se o diretório base existe
                base_path = file_pattern.split("*")[0]
                if os.path.exists(base_path) and any(os.scandir(base_path)):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{file_pattern}')"
                    )
                else:
                    conn.execute(
                        f"CREATE OR REPLACE TABLE {table_name} (dummy INTEGER)"
                    )
            else:
                if os.path.exists(file_pattern):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{file_pattern}')"
                    )
                else:
                    conn.execute(
                        f"CREATE OR REPLACE TABLE {table_name} (dummy INTEGER)"
                    )
        except Exception:
            # Em caso de qualquer erro de metadados, inicializa tabela vazia para evitar quebras de rota
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} (dummy INTEGER)")

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
