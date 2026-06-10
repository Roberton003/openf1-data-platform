from datetime import datetime

import duckdb
import pandas as pd
from pydantic import BaseModel

from src.ingestion.process import (
    TELEMETRY_SCHEMA,
    init_duckdb_schema,
    validate_pydantic_batch,
    validate_vectorized_batch,
)
from src.ingestion.schemas import DriverContract


class DummyContract(BaseModel):
    id: int
    name: str


def test_validate_pydantic_batch():
    # 1. Dados válidos
    df_valid = pd.DataFrame(
        [
            {
                "driver_number": 44,
                "full_name": "Lewis Hamilton",
                "name_acronym": "HAM",
                "team_name": "Ferrari",
                "country_code": "GBR",
            }
        ]
    )
    df_v, df_i = validate_pydantic_batch(df_valid, DriverContract, "drivers")

    assert not df_v.empty
    assert df_i.empty
    assert df_v.iloc[0]["driver_number"] == 44
    assert df_v.iloc[0]["name_acronym"] == "HAM"

    # 2. Dados inválidos (driver_number ausente ou tipo errado)
    df_invalid = pd.DataFrame(
        [{"full_name": "Lewis Hamilton", "name_acronym": "HAM", "team_name": "Ferrari"}]
    )  # driver_number é obrigatório
    df_v, df_i = validate_pydantic_batch(df_invalid, DriverContract, "drivers")

    assert df_v.empty
    assert not df_i.empty
    assert "driver_number" in df_i.iloc[0]["error_detail"]


def test_validate_vectorized_batch():
    # 1. Dados de telemetria válidos
    date_val = datetime(2025, 3, 16, 12, 0, 0)
    df_tel = pd.DataFrame(
        [
            {
                "session_key": 9400,
                "driver_number": 1,
                "date": date_val,
                "speed": 312,
                "rpm": 11800,
                "n_gear": 7,
                "throttle": 98.5,
                "brake": 0.0,
                "drs": 12,
            }
        ]
    )

    df_v, df_i = validate_vectorized_batch(
        df_tel, TELEMETRY_SCHEMA, ["session_key", "driver_number", "date"]
    )

    assert not df_v.empty
    assert df_i.empty
    assert df_v.iloc[0]["speed"] == 312
    assert df_v.iloc[0]["rpm"] == 11800

    # 2. Dados de telemetria inválidos (chave session_key nula)
    df_tel_invalid = pd.DataFrame(
        [
            {
                "session_key": None,
                "driver_number": 1,
                "date": date_val,
                "speed": 312,
                "rpm": 11800,
            }
        ]
    )

    df_v, df_i = validate_vectorized_batch(
        df_tel_invalid, TELEMETRY_SCHEMA, ["session_key", "driver_number", "date"]
    )

    assert df_v.empty
    assert not df_i.empty
    assert "Valor nulo" in df_i.iloc[0]["error_detail"]


def test_init_duckdb_schema():
    # Testar se a inicialização do banco cria todas as tabelas corretamente no DuckDB in-memory
    conn = duckdb.connect(database=":memory:")
    init_duckdb_schema(conn)

    # Verificar tabelas
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    assert "dim_sessions" in table_names
    assert "dim_drivers" in table_names
    assert "dim_stints" in table_names
    assert "dim_weather" in table_names
    assert "fact_car_telemetry" in table_names
    assert "fact_pit_stops" in table_names
    assert "fact_race_control" in table_names
    assert "fact_intervals" in table_names
    assert "fact_pipeline_execution" in table_names

    conn.close()


def test_dim_drivers_upsert():
    # Testar se o mecanismo de ON CONFLICT (Upsert) atualiza os dados do piloto em vez de lançar erro
    conn = duckdb.connect(database=":memory:")
    init_duckdb_schema(conn)

    # 1. Inserir piloto inicial (Lewis Hamilton na Mercedes)
    df_initial = pd.DataFrame(
        [
            {
                "driver_number": 44,
                "full_name": "Lewis Hamilton",
                "name_acronym": "HAM",
                "team_name": "Mercedes",
                "country_code": "GBR",
            }
        ]
    )

    conn.execute(
        """
        INSERT INTO dim_drivers
        SELECT driver_number, full_name, name_acronym, team_name, country_code FROM df_initial
    """
    )

    # Verificar inserção
    driver = conn.execute(
        "SELECT team_name FROM dim_drivers WHERE driver_number = 44"
    ).fetchone()
    assert driver[0] == "Mercedes"

    # 2. Executar Upsert atualizando a equipe (Lewis Hamilton na Ferrari)
    df_update = pd.DataFrame(
        [
            {
                "driver_number": 44,
                "full_name": "Lewis Hamilton",
                "name_acronym": "HAM",
                "team_name": "Ferrari",
                "country_code": "GBR",
            }
        ]
    )

    conn.execute(
        """
        INSERT INTO dim_drivers
        SELECT driver_number, full_name, name_acronym, team_name, country_code FROM df_update
        ON CONFLICT (driver_number) DO UPDATE SET
            full_name = excluded.full_name,
            name_acronym = excluded.name_acronym,
            team_name = excluded.team_name,
            country_code = excluded.country_code
    """
    )

    # Verificar se atualizou e manteve apenas 1 registro
    drivers_count = conn.execute("SELECT COUNT(*) FROM dim_drivers").fetchone()[0]
    assert drivers_count == 1

    driver_updated = conn.execute(
        "SELECT team_name FROM dim_drivers WHERE driver_number = 44"
    ).fetchone()
    assert driver_updated[0] == "Ferrari"

    conn.close()
