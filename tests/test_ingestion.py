from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from src.ingestion.process import (
    TELEMETRY_SCHEMA,
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


def test_driver_merge_logic():
    # Testar a lógica de merge de drivers em lote que antes era feita via ON CONFLICT do DuckDB
    # Representa a lógica do process.py
    df_existing = pd.DataFrame(
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

    driver_nums = df_valid["driver_number"].tolist()
    # Executa a lógica de exclusão do existente antes de concatenar (simula upsert)
    df_existing_filtered = df_existing[~df_existing["driver_number"].isin(driver_nums)]
    df_final = pd.concat([df_existing_filtered, df_valid], ignore_index=True)

    assert len(df_final) == 1
    assert df_final.iloc[0]["team_name"] == "Ferrari"
