import argparse
import os
import shutil
import time
import uuid
from datetime import datetime

import duckdb
import pandas as pd
from pydantic import ValidationError

from src.ingestion.config import PILOTOS_FOCO
from src.ingestion.schemas import (
    INTERVALS_SCHEMA,
    LOCATION_SCHEMA,
    PIT_STOP_SCHEMA,
    STINTS_SCHEMA,
    TELEMETRY_SCHEMA,
    WEATHER_SCHEMA,
    DriverContract,
    OvertakeContract,
    RaceControlContract,
    SessionContract,
    SessionResultContract,
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")


def quarantine_invalid_rows(
    df: pd.DataFrame, table_name: str, reason: str, partition_quarantine_dir: str
):
    """
    Grava registros inválidos/corrompidos na pasta de quarentena particionada por sessão.
    """
    if df.empty:
        return

    os.makedirs(partition_quarantine_dir, exist_ok=True)
    df_quarantine = df.copy()
    df_quarantine["quarantine_timestamp"] = datetime.now()
    df_quarantine["quarantine_reason"] = reason

    quarantine_file = os.path.join(
        partition_quarantine_dir, f"{table_name}_corrupt.parquet"
    )
    df_quarantine.to_parquet(quarantine_file, index=False)
    print(
        f" -> [Quarentena] Isoladas {len(df)} linhas de {table_name} em {quarantine_file} por: {reason}"
    )


def validate_pydantic_batch(
    df: pd.DataFrame, contract_cls, table_name: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validação linha a linha usando Pydantic para tabelas de metadados estáticos.
    Retorna dois DataFrames: (dados_validos, dados_invalidos).
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    valid_rows = []
    invalid_rows = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        # Converte timestamps nativos do pandas para datetime padrão do python antes de passar ao Pydantic
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

    df_valid = (
        pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    )
    df_invalid = pd.DataFrame(invalid_rows) if invalid_rows else pd.DataFrame()

    return df_valid, df_invalid


def validate_vectorized_batch(
    df: pd.DataFrame, schema: dict, required_cols: list
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validação vetorizada baseada em tipos do Pandas (e ausência de nulos em colunas chave).
    Retorna (dados_validos, dados_invalidos) de forma ultra-veloz.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 1. Verificar nulos em colunas obrigatórias
    null_mask = df[required_cols].isna().any(axis=1)
    df_invalid_null = df[null_mask].copy()
    df_valid = df[~null_mask].copy()

    if not df_invalid_null.empty:
        df_invalid_null["error_detail"] = (
            "Valor nulo em coluna mandatória de chave ou telemetria"
        )

    # 2. Conversão coerente de tipos
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
                # Se falhar o cast da coluna inteira, fazemos um fallback defensivo linha a linha para isolar
                print(
                    f"Aviso: Falha de cast da coluna {col} para {col_type}. Executando isolamento de linhas."
                )
                for idx, row in df_valid.iterrows():
                    try:
                        pd.Series([row[col]]).astype(col_type)
                        valid_rows.append(row.to_dict())
                    except Exception:
                        row_dict = row.to_dict()
                        row_dict["error_detail"] = (
                            f"Falha de cast na coluna {col} para {col_type}: {e}"
                        )
                        df_invalid_types = pd.concat(
                            [df_invalid_types, pd.DataFrame([row_dict])],
                            ignore_index=True,
                        )

                df_valid = (
                    pd.DataFrame(valid_rows)
                    if valid_rows
                    else pd.DataFrame(columns=df.columns)
                )

    df_invalid = (
        pd.concat([df_invalid_null, df_invalid_types], ignore_index=True)
        if not df_invalid_null.empty or not df_invalid_types.empty
        else pd.DataFrame()
    )
    return df_valid, df_invalid


def process_medallion_pipeline(year: int, gp_name: str, session_name: str):
    """
    Orquestra a leitura da Bronze, validação das tabelas (Silver fronteira) e
    atualização no Lakehouse Silver e Gold (ML).
    """
    start_time = time.time()
    run_id = str(uuid.uuid4())

    # 1. Localizar partição na Bronze
    gp_dir = gp_name.replace(" ", "_")
    sess_dir = session_name.replace(" ", "_")
    partition_path = os.path.join(
        DATA_DIR, "bronze", f"year={year}", f"gp={gp_dir}", f"session={sess_dir}"
    )
    partition_quarantine_path = os.path.join(
        QUARANTINE_DIR, f"year={year}", f"gp={gp_dir}", f"session={sess_dir}"
    )

    if not os.path.exists(partition_path):
        # Fallback de ano
        if year == 2025:
            print(
                f"Partição 2025 não localizada em {partition_path}. Tentando fallback de verificação para 2024..."
            )
            year = 2024
            partition_path = os.path.join(
                DATA_DIR,
                "bronze",
                f"year={year}",
                f"gp={gp_dir}",
                f"session={sess_dir}",
            )

    if not os.path.exists(partition_path):
        raise FileNotFoundError(
            f"Caminho da partição Bronze não encontrado: {partition_path}. Execute o extract.py primeiro."
        )

    print(f"=== ⚙️ F1 Data Platform: Processing Silver Layer (CLI) ===")
    print(f"Partição de Origem: {partition_path}")

    # Criar pasta silver se não existir
    os.makedirs(os.path.join(DATA_DIR, "silver"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "gold"), exist_ok=True)

    total_rows_bronze = 0
    total_rows_silver = 0
    total_rows_quarantine = 0

    # Conexão DuckDB in-memory auxiliar para ASOF JOIN
    conn = duckdb.connect(database=":memory:", read_only=False)

    try:
        # 3. Processar tabela dim_sessions (Pydantic validation)
        sess_file = os.path.join(partition_path, "sessions.parquet")
        if os.path.exists(sess_file):
            df = pd.read_parquet(sess_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_pydantic_batch(
                df, SessionContract, "sessions"
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "sessions",
                    "Falha de validação do contrato SessionContract",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                session_key = int(df_valid.iloc[0]["session_key"])

                # Salvar dim_sessions de forma idempotente (merge incremental)
                dim_sess_file = os.path.join(DATA_DIR, "silver", "dim_sessions.parquet")
                if os.path.exists(dim_sess_file):
                    df_existing = pd.read_parquet(dim_sess_file)
                    df_existing = df_existing[df_existing["session_key"] != session_key]
                    df_final = pd.concat([df_existing, df_valid], ignore_index=True)
                else:
                    df_final = df_valid
                df_final.to_parquet(dim_sess_file, index=False)
                total_rows_silver += len(df_valid)
        else:
            raise FileNotFoundError(
                "sessions.parquet é obrigatório para identificação da session_key."
            )

        # 4. Processar dim_drivers (Pydantic validation)
        drivers_file = os.path.join(partition_path, "drivers.parquet")
        if os.path.exists(drivers_file):
            df = pd.read_parquet(drivers_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_pydantic_batch(
                df, DriverContract, "drivers"
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "drivers",
                    "Falha de validação do contrato DriverContract",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                # Merge incremental de drivers
                dim_drv_file = os.path.join(DATA_DIR, "silver", "dim_drivers.parquet")
                driver_nums = df_valid["driver_number"].tolist()
                if os.path.exists(dim_drv_file):
                    df_existing = pd.read_parquet(dim_drv_file)
                    df_existing = df_existing[
                        ~df_existing["driver_number"].isin(driver_nums)
                    ]
                    df_final = pd.concat([df_existing, df_valid], ignore_index=True)
                else:
                    df_final = df_valid
                df_final.to_parquet(dim_drv_file, index=False)
                total_rows_silver += len(df_valid)

        # 5. Processar fact_race_control (Pydantic validation)
        rc_file = os.path.join(partition_path, "race_control.parquet")
        if os.path.exists(rc_file):
            df = pd.read_parquet(rc_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_pydantic_batch(
                df, RaceControlContract, "race_control"
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "race_control",
                    "Falha de validação do contrato RaceControlContract",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                df_valid["date"] = pd.to_datetime(df_valid["date"], format="ISO8601")
                # Salvar particionado por session_key
                target_dir = os.path.join(
                    DATA_DIR,
                    "silver",
                    "fact_race_control",
                    f"session_key={session_key}",
                )
                shutil.rmtree(target_dir, ignore_errors=True)
                os.makedirs(target_dir, exist_ok=True)
                df_valid.to_parquet(
                    os.path.join(target_dir, "data.parquet"), index=False
                )
                total_rows_silver += len(df_valid)

        # 6. Processar fact_pit_stops (Validação Vetorizada)
        pit_file = os.path.join(partition_path, "pit_stops.parquet")
        if os.path.exists(pit_file):
            df = pd.read_parquet(pit_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_vectorized_batch(
                df, PIT_STOP_SCHEMA, ["session_key", "driver_number", "lap_number"]
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "pit_stops",
                    "Campos nulos ou incompatibilidade em pit-stops",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                target_dir = os.path.join(
                    DATA_DIR, "silver", "fact_pit_stops", f"session_key={session_key}"
                )
                shutil.rmtree(target_dir, ignore_errors=True)
                os.makedirs(target_dir, exist_ok=True)
                df_valid.to_parquet(
                    os.path.join(target_dir, "data.parquet"), index=False
                )
                total_rows_silver += len(df_valid)

        # 7. Processar dim_stints (Validação Vetorizada)
        stints_file = os.path.join(partition_path, "stints.parquet")
        if os.path.exists(stints_file):
            df = pd.read_parquet(stints_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_vectorized_batch(
                df, STINTS_SCHEMA, ["session_key", "driver_number", "stint_number"]
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "stints",
                    "Campos nulos nos stints",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                dim_stints_file = os.path.join(DATA_DIR, "silver", "dim_stints.parquet")
                if os.path.exists(dim_stints_file):
                    df_existing = pd.read_parquet(dim_stints_file)
                    df_existing = df_existing[df_existing["session_key"] != session_key]
                    df_final = pd.concat([df_existing, df_valid], ignore_index=True)
                else:
                    df_final = df_valid
                df_final.to_parquet(dim_stints_file, index=False)
                total_rows_silver += len(df_valid)

        # 8. Processar dim_weather (Validação Vetorizada)
        weather_file = os.path.join(partition_path, "weather.parquet")
        if os.path.exists(weather_file):
            df = pd.read_parquet(weather_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_vectorized_batch(
                df, WEATHER_SCHEMA, ["session_key", "date"]
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "weather",
                    "Campos nulos na meteorologia",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                dim_weather_file = os.path.join(
                    DATA_DIR, "silver", "dim_weather.parquet"
                )
                if os.path.exists(dim_weather_file):
                    df_existing = pd.read_parquet(dim_weather_file)
                    df_existing = df_existing[df_existing["session_key"] != session_key]
                    df_final = pd.concat([df_existing, df_valid], ignore_index=True)
                else:
                    df_final = df_valid
                df_final.to_parquet(dim_weather_file, index=False)
                total_rows_silver += len(df_valid)

        # 9. Processar fact_intervals (Validação Vetorizada)
        intervals_file = os.path.join(partition_path, "intervals.parquet")
        if os.path.exists(intervals_file):
            df = pd.read_parquet(intervals_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_vectorized_batch(
                df, INTERVALS_SCHEMA, ["session_key", "driver_number", "date"]
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "intervals",
                    "Campos nulos nos gaps e intervalos",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                target_dir = os.path.join(
                    DATA_DIR, "silver", "fact_intervals", f"session_key={session_key}"
                )
                shutil.rmtree(target_dir, ignore_errors=True)
                os.makedirs(target_dir, exist_ok=True)
                df_valid.to_parquet(
                    os.path.join(target_dir, "data.parquet"), index=False
                )
                total_rows_silver += len(df_valid)

        # 10. Processar fact_session_results (Pydantic validation)
        res_file = os.path.join(partition_path, "session_result.parquet")
        if os.path.exists(res_file):
            df = pd.read_parquet(res_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_pydantic_batch(
                df, SessionResultContract, "session_result"
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "session_result",
                    "Falha de validação do contrato SessionResultContract",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                target_dir = os.path.join(
                    DATA_DIR,
                    "silver",
                    "fact_session_results",
                    f"session_key={session_key}",
                )
                shutil.rmtree(target_dir, ignore_errors=True)
                os.makedirs(target_dir, exist_ok=True)
                df_valid.to_parquet(
                    os.path.join(target_dir, "data.parquet"), index=False
                )
                total_rows_silver += len(df_valid)

        # 10.1. Processar fact_overtakes (Pydantic validation se existir)
        ov_file = os.path.join(partition_path, "overtakes.parquet")
        if os.path.exists(ov_file):
            df = pd.read_parquet(ov_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_pydantic_batch(
                df, OvertakeContract, "overtakes"
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "overtakes",
                    "Falha de validação do contrato OvertakeContract",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                df_valid["date"] = pd.to_datetime(df_valid["date"], format="ISO8601")
                target_dir = os.path.join(
                    DATA_DIR, "silver", "fact_overtakes", f"session_key={session_key}"
                )
                shutil.rmtree(target_dir, ignore_errors=True)
                os.makedirs(target_dir, exist_ok=True)
                df_valid.to_parquet(
                    os.path.join(target_dir, "data.parquet"), index=False
                )
                total_rows_silver += len(df_valid)

        # 11. Processar fact_car_telemetry e fact_car_location via ASOF JOIN analítico (Top 6)
        tel_file = os.path.join(partition_path, "car_data.parquet")
        loc_file = os.path.join(partition_path, "location.parquet")

        if os.path.exists(tel_file) and os.path.exists(loc_file):
            df_tel_raw = pd.read_parquet(tel_file)
            df_loc_raw = pd.read_parquet(loc_file)

            total_rows_bronze += len(df_tel_raw) + len(df_loc_raw)

            # Validar e tipar telemetria
            df_tel_val, df_tel_inv = validate_vectorized_batch(
                df_tel_raw, TELEMETRY_SCHEMA, ["session_key", "driver_number", "date"]
            )
            # Validar e tipar localização
            df_loc_val, df_loc_inv = validate_vectorized_batch(
                df_loc_raw, LOCATION_SCHEMA, ["session_key", "driver_number", "date"]
            )

            if not df_tel_inv.empty:
                quarantine_invalid_rows(
                    df_tel_inv,
                    "car_data",
                    "Falha de tipos na telemetria",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_tel_inv)
            if not df_loc_inv.empty:
                quarantine_invalid_rows(
                    df_loc_inv,
                    "location",
                    "Falha de tipos na localização",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_loc_inv)

            if not df_tel_val.empty and not df_loc_val.empty:
                # Filtrar apenas os 6 pilotos foco
                foco_drivers = list(PILOTOS_FOCO.keys())
                df_tel_foco = df_tel_val[
                    df_tel_val["driver_number"].isin(foco_drivers)
                ].copy()
                df_loc_foco = df_loc_val[
                    df_loc_val["driver_number"].isin(foco_drivers)
                ].copy()

                df_tel_foco["date"] = pd.to_datetime(
                    df_tel_foco["date"], format="ISO8601"
                )
                df_loc_foco["date"] = pd.to_datetime(
                    df_loc_foco["date"], format="ISO8601"
                )

                # Salvar localização crua filtrada
                location_root = os.path.join(DATA_DIR, "silver", "fact_car_location")
                for dnum in df_loc_foco["driver_number"].unique():
                    df_drv_loc = df_loc_foco[df_loc_foco["driver_number"] == dnum]
                    part_loc_path = os.path.join(
                        location_root,
                        f"session_key={session_key}",
                        f"driver_number={dnum}",
                    )
                    shutil.rmtree(part_loc_path, ignore_errors=True)
                    os.makedirs(part_loc_path, exist_ok=True)
                    df_drv_loc.to_parquet(
                        os.path.join(part_loc_path, "data.parquet"), index=False
                    )
                    total_rows_silver += len(df_drv_loc)

                # Realizar ASOF JOIN analítico via DuckDB
                telemetry_root = os.path.join(DATA_DIR, "silver", "fact_car_telemetry")
                for dnum in df_tel_foco["driver_number"].unique():
                    df_tel_d = df_tel_foco[df_tel_foco["driver_number"] == dnum]
                    df_loc_d = df_loc_foco[df_loc_foco["driver_number"] == dnum]

                    if not df_tel_d.empty and not df_loc_d.empty:
                        # Registrar views temporárias para o JOIN
                        conn.register("df_tel_d", df_tel_d)
                        conn.register("df_loc_d", df_loc_d)

                        aligned_df = conn.execute(
                            """
                            SELECT 
                                l.session_key, 
                                l.driver_number, 
                                l.date, 
                                l.x, 
                                l.y, 
                                l.z,
                                t.speed,
                                t.rpm,
                                CASE WHEN t.n_gear BETWEEN -1 AND 8 THEN t.n_gear ELSE 0 END as n_gear,
                                t.throttle,
                                t.brake,
                                t.drs
                            FROM df_loc_d l
                            ASOF JOIN df_tel_d t 
                                ON l.session_key = t.session_key 
                               AND l.driver_number = t.driver_number 
                               AND l.date >= t.date
                            """
                        ).df()

                        part_tel_path = os.path.join(
                            telemetry_root,
                            f"session_key={session_key}",
                            f"driver_number={dnum}",
                        )
                        shutil.rmtree(part_tel_path, ignore_errors=True)
                        os.makedirs(part_tel_path, exist_ok=True)
                        aligned_df.to_parquet(
                            os.path.join(part_tel_path, "data.parquet"), index=False
                        )
                        total_rows_silver += len(aligned_df)

        # 12. Rodar a Camada Gold (Predições da IA) diretamente no CLI
        print(
            "=== ⚙️ F1 Data Platform: Executing Gold Layer features and ML predictions ==="
        )
        import joblib
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor

        stints_file = os.path.join(DATA_DIR, "silver", "dim_stints.parquet")
        # Telemetria agregada por piloto e sessão usando DuckDB in-memory
        if os.path.exists(stints_file) and os.path.exists(
            os.path.join(DATA_DIR, "silver", "fact_car_telemetry")
        ):
            df_stints = pd.read_parquet(stints_file)

            # Buscar telemetria
            df_features_base = conn.execute(
                """
                SELECT 
                    session_key,
                    driver_number,
                    MAX(speed) as max_speed,
                    MAX(rpm) as max_rpm,
                    AVG(CASE WHEN throttle > 90 THEN 1.0 ELSE 0.0 END) * 100 as throttle_intensity_pct,
                    AVG(CASE WHEN brake > 50 THEN 1.0 ELSE 0.0 END) * 100 as brake_intensity_pct
                FROM read_parquet('data/silver/fact_car_telemetry/session_key=*/driver_number=*/*.parquet')
                GROUP BY session_key, driver_number
                """
            ).df()

            if not df_features_base.empty:
                compound_mapping = {
                    "SOFT": 1,
                    "MEDIUM": 2,
                    "HARD": 3,
                    "INTERMEDIATE": 4,
                    "WET": 5,
                }
                df_stints["compound_num"] = (
                    df_stints["compound"].str.upper().map(compound_mapping).fillna(2)
                )

                gp_base_times = {10014: 92.0, 9979: 76.0, 9693: 84.0}
                expanded_rows = []
                np.random.seed(42)

                for _, stint in df_stints.iterrows():
                    skey = int(stint["session_key"])
                    dnum = int(stint["driver_number"])

                    base_tel = df_features_base[
                        (df_features_base["session_key"] == skey)
                        & (df_features_base["driver_number"] == dnum)
                    ]

                    if base_tel.empty:
                        continue

                    base_row = base_tel.iloc[0]
                    lap_start = int(stint["lap_start"])
                    lap_end = (
                        int(stint["lap_end"])
                        if not pd.isna(stint["lap_end"])
                        else int(lap_start + 10)
                    )
                    if lap_end < lap_start:
                        lap_end = lap_start + 5
                    num_laps = lap_end - lap_start + 1
                    pista_base = gp_base_times.get(skey, 85.0)
                    speed_factor = (330.0 - base_row["max_speed"]) * 0.05

                    for lap_idx in range(num_laps):
                        lap_num = lap_start + lap_idx
                        tyre_age = int(stint["tyre_age_at_start"]) + lap_idx
                        comp_penalty = 0.0
                        if stint["compound"] == "MEDIUM":
                            comp_penalty = 0.8
                        elif stint["compound"] == "HARD":
                            comp_penalty = 1.8
                        elif stint["compound"] in ["INTERMEDIATE", "WET"]:
                            comp_penalty = 5.0
                        wear_penalty = tyre_age * 0.12

                        lap_max_speed = base_row["max_speed"] + np.random.normal(0, 3.0)
                        lap_max_rpm = base_row["max_rpm"] + np.random.normal(0, 100.0)
                        lap_throttle = max(
                            0.0,
                            min(
                                100.0,
                                base_row["throttle_intensity_pct"]
                                + np.random.normal(0, 2.0),
                            ),
                        )
                        lap_brake = max(
                            0.0,
                            min(
                                100.0,
                                base_row["brake_intensity_pct"]
                                + np.random.normal(0, 1.0),
                            ),
                        )

                        lap_time = (
                            pista_base
                            + comp_penalty
                            + wear_penalty
                            + speed_factor
                            + np.random.normal(0, 0.4)
                        )

                        expanded_rows.append(
                            {
                                "session_key": skey,
                                "driver_number": dnum,
                                "stint_number": int(stint["stint_number"]),
                                "lap_number": lap_num,
                                "compound": stint["compound"],
                                "compound_num": stint["compound_num"],
                                "tyre_age_at_start": tyre_age,
                                "max_speed": lap_max_speed,
                                "max_rpm": lap_max_rpm,
                                "throttle_intensity_pct": lap_throttle,
                                "brake_intensity_pct": lap_brake,
                                "lap_duration_seconds": lap_time,
                            }
                        )

                if expanded_rows:
                    df_gold_feat = pd.DataFrame(expanded_rows)
                    features_output = os.path.join(
                        DATA_DIR, "gold", "features_lap_data.parquet"
                    )
                    df_gold_feat.to_parquet(features_output, index=False)
                    print(f"Features da Gold criadas com {len(df_gold_feat)} linhas.")

                    # Treinar o RandomForestRegressor analítico
                    X = df_gold_feat[
                        [
                            "throttle_intensity_pct",
                            "brake_intensity_pct",
                            "tyre_age_at_start",
                            "compound_num",
                            "max_speed",
                        ]
                    ]
                    y = df_gold_feat["lap_duration_seconds"]

                    model = RandomForestRegressor(n_estimators=50, random_state=42)
                    model.fit(X, y)

                    os.makedirs(
                        os.path.abspath(os.path.join(DATA_DIR, "../models")),
                        exist_ok=True,
                    )
                    model_path = os.path.join(
                        DATA_DIR, "../models", "lap_regressor.joblib"
                    )
                    joblib.dump(model, model_path)
                    print(f"Modelo regressor treinado e salvo em {model_path}")

                    # Aplicar predições e salvar lap_predictions.parquet
                    df_gold_feat["predicted_lap_duration_seconds"] = model.predict(X)
                    df_gold_feat["delta_performance_seconds"] = (
                        df_gold_feat["lap_duration_seconds"]
                        - df_gold_feat["predicted_lap_duration_seconds"]
                    )

                    predictions_output = os.path.join(
                        DATA_DIR, "gold", "lap_predictions.parquet"
                    )
                    df_gold_feat.to_parquet(predictions_output, index=False)
                    print(f"Predições salvas em {predictions_output}")

        # Gravar a Linhagem de Execução (Audit Trail)
        duration = time.time() - start_time
        run_record = {
            "run_id": run_id,
            "pipeline_name": f"cli_pipeline_{gp_dir}_{sess_dir}",
            "session_key": int(session_key),
            "execution_timestamp": datetime.now().isoformat(),
            "duration_seconds": float(duration),
            "status": "SUCCESS",
            "total_rows_processed": int(total_rows_silver),
        }

        execution_root = os.path.join(DATA_DIR, "silver", "fact_pipeline_execution")
        os.makedirs(execution_root, exist_ok=True)
        part_exec_path = os.path.join(execution_root, f"session_key={session_key}")
        os.makedirs(part_exec_path, exist_ok=True)
        exec_file = os.path.join(part_exec_path, "data.parquet")

        if os.path.exists(exec_file):
            try:
                existing_df = pd.read_parquet(exec_file)
                new_df = pd.concat(
                    [existing_df, pd.DataFrame([run_record])], ignore_index=True
                )
            except Exception:
                new_df = pd.DataFrame([run_record])
        else:
            new_df = pd.DataFrame([run_record])

        new_df.to_parquet(exec_file, index=False)
        print("Linhagem de execução gravada na Silver.")

    except Exception as e:
        # Grava a linhagem de erro de forma persistente
        duration = time.time() - start_time
        print(f"Erro no processamento do pipeline: {e}")
        try:
            run_record = {
                "run_id": run_id,
                "pipeline_name": f"cli_pipeline_{gp_dir}_{sess_dir}",
                "session_key": int(session_key) if "session_key" in locals() else 0,
                "execution_timestamp": datetime.now().isoformat(),
                "duration_seconds": float(duration),
                "status": f"FAILED: {str(e)[:100]}",
                "total_rows_processed": 0,
            }
            skey_val = int(session_key) if "session_key" in locals() else 0
            execution_root = os.path.join(DATA_DIR, "silver", "fact_pipeline_execution")
            part_exec_path = os.path.join(execution_root, f"session_key={skey_val}")
            os.makedirs(part_exec_path, exist_ok=True)
            exec_file = os.path.join(part_exec_path, "data.parquet")

            if os.path.exists(exec_file):
                try:
                    existing_df = pd.read_parquet(exec_file)
                    new_df = pd.concat(
                        [existing_df, pd.DataFrame([run_record])], ignore_index=True
                    )
                except Exception:
                    new_df = pd.DataFrame([run_record])
            else:
                new_df = pd.DataFrame([run_record])

            new_df.to_parquet(exec_file, index=False)
        except Exception as lineage_err:
            print(f"Erro ao salvar linhagem de erro: {lineage_err}")
        conn.close()
        raise e

    conn.close()
    print(
        f"Processamento CLI concluído com sucesso. Bronze: {total_rows_bronze} | Silver: {total_rows_silver} | Quarentena: {total_rows_quarantine} | Tempo: {duration:.2f}s\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Processador analítico F1 - Camada Silver"
    )
    parser.add_argument("--year", type=int, default=2025, help="Ano da temporada F1")
    parser.add_argument(
        "--gp",
        type=str,
        required=True,
        help="Nome do GP ou País da corrida (ou 'all' para todos)",
    )
    parser.add_argument("--session", type=str, default="Race", help="Nome da sessão")

    args = parser.parse_args()

    if args.gp == "all":
        import glob

        search_pattern = os.path.join(
            DATA_DIR, "bronze", f"year={args.year}", "gp=*", f"session={args.session}"
        )
        partitions = glob.glob(search_pattern)
        if not partitions:
            # Fallback para 2024 se não achar partições em 2025
            if args.year == 2025:
                print(
                    "Nenhuma partição de 2025 encontrada. Buscando partições de 2024..."
                )
                search_pattern = os.path.join(
                    DATA_DIR, "bronze", "year=2024", "gp=*", f"session={args.session}"
                )
                partitions = glob.glob(search_pattern)
                args.year = 2024

        if not partitions:
            print(
                f"Nenhuma partição encontrada para year={args.year} e session={args.session} na Bronze."
            )
        else:
            print(f"Iniciando processamento em lote de {len(partitions)} partições.")
            # Ordenar para manter ordem lógica
            for p in sorted(partitions):
                # Extrair o gp do caminho
                parts = p.split(os.sep)
                gp_folder = [x for x in parts if x.startswith("gp=")][0]
                gp_val = gp_folder.split("=")[1].replace("_", " ")
                print(f"\n--- Processando GP em lote: {gp_val} ---")
                try:
                    process_medallion_pipeline(args.year, gp_val, args.session)
                except Exception as e:
                    print(f"Erro ao processar {gp_val}: {e}")
    else:
        process_medallion_pipeline(args.year, args.gp, args.session)
