import argparse
import os
import shutil
import time
import uuid
from datetime import datetime

import duckdb
import pandas as pd
from pydantic import ValidationError

from src.ingestion.schemas import (
    INTERVALS_SCHEMA,
    PIT_STOP_SCHEMA,
    STINTS_SCHEMA,
    TELEMETRY_SCHEMA,
    WEATHER_SCHEMA,
    DriverContract,
    RaceControlContract,
    SessionContract,
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
SILVER_DB_PATH = os.path.join(DATA_DIR, "silver", "openf1_silver.duckdb")
SILVER_DB_NEW_PATH = os.path.join(DATA_DIR, "silver", "openf1_silver.new.duckdb")
QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")


def init_duckdb_schema(conn: duckdb.DuckDBPyConnection):
    """
    Inicializa as tabelas do Star Schema no DuckDB temporário caso não existam.
    """
    # 1. Tabela de Metadados de Execução (Linhagem de dados)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_pipeline_execution (
            execution_timestamp TIMESTAMP,
            run_id VARCHAR,
            pipeline_name VARCHAR,
            duration_seconds DOUBLE,
            rows_bronze INTEGER,
            rows_silver INTEGER,
            rows_quarantine INTEGER,
            status VARCHAR
        )
    """
    )

    # 2. Dimensões
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_sessions (
            session_key INTEGER PRIMARY KEY,
            year INTEGER,
            session_name VARCHAR,
            session_type VARCHAR,
            circuit_key INTEGER,
            circuit_short_name VARCHAR,
            country_name VARCHAR
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_drivers (
            driver_number INTEGER PRIMARY KEY,
            full_name VARCHAR,
            name_acronym VARCHAR,
            team_name VARCHAR,
            country_code VARCHAR
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_stints (
            session_key INTEGER,
            driver_number INTEGER,
            stint_number INTEGER,
            compound VARCHAR,
            lap_start INTEGER,
            lap_end INTEGER,
            tyre_age_at_start INTEGER,
            PRIMARY KEY (session_key, driver_number, stint_number)
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_weather (
            session_key INTEGER,
            date TIMESTAMP,
            air_temperature DOUBLE,
            track_temperature DOUBLE,
            humidity DOUBLE,
            wind_speed DOUBLE,
            rainfall INTEGER,
            PRIMARY KEY (session_key, date)
        )
    """
    )

    # 3. Fatos
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_car_telemetry (
            session_key INTEGER,
            driver_number INTEGER,
            date TIMESTAMP,
            speed INTEGER,
            rpm INTEGER,
            n_gear INTEGER,
            throttle DOUBLE,
            brake DOUBLE,
            drs INTEGER,
            PRIMARY KEY (session_key, driver_number, date)
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_pit_stops (
            session_key INTEGER,
            driver_number INTEGER,
            lap_number INTEGER,
            stop_duration DOUBLE,
            lane_duration DOUBLE,
            pit_duration DOUBLE,
            date TIMESTAMP,
            PRIMARY KEY (session_key, driver_number, lap_number)
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_race_control (
            session_key INTEGER,
            driver_number INTEGER,
            category VARCHAR,
            flag VARCHAR,
            message VARCHAR,
            date TIMESTAMP
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_intervals (
            session_key INTEGER,
            driver_number INTEGER,
            gap_to_leader VARCHAR,
            interval VARCHAR,
            date TIMESTAMP,
            PRIMARY KEY (session_key, driver_number, date)
        )
    """
    )


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
    atualização atômica (Hot-Swap) do DuckDB local.
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

    print(f"=== ⚙️ F1 Data Platform: Processing Silver Layer ===")
    print(f"Partição de Origem: {partition_path}")

    # 2. Criar cópia do banco para gravação (Hot-Swap DEC-015)
    os.makedirs(os.path.dirname(SILVER_DB_PATH), exist_ok=True)
    if os.path.exists(SILVER_DB_PATH):
        shutil.copyfile(SILVER_DB_PATH, SILVER_DB_NEW_PATH)
        print(
            "Copiado banco principal existente para instância temporária de atualização."
        )
    else:
        # Se não existe, inicia um arquivo novo
        if os.path.exists(SILVER_DB_NEW_PATH):
            os.remove(SILVER_DB_NEW_PATH)
        print("Criando novo banco temporário DuckDB.")

    # Conectar ao banco temporário de escrita
    conn = duckdb.connect(database=SILVER_DB_NEW_PATH, read_only=False)
    init_duckdb_schema(conn)

    total_rows_bronze = 0
    total_rows_silver = 0
    total_rows_quarantine = 0

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
                # Obter a session_key do processamento corrente
                session_key = int(df_valid.iloc[0]["session_key"])

                # Deletar dados antigos da mesma sessão para garantir idempotência do pipeline
                print(
                    f"Limpando dados históricos da session_key={session_key} para gravação idempotente..."
                )
                conn.execute(
                    "DELETE FROM dim_sessions WHERE session_key = ?", (session_key,)
                )
                conn.execute(
                    "DELETE FROM dim_stints WHERE session_key = ?", (session_key,)
                )
                conn.execute(
                    "DELETE FROM dim_weather WHERE session_key = ?", (session_key,)
                )
                conn.execute(
                    "DELETE FROM fact_car_telemetry WHERE session_key = ?",
                    (session_key,),
                )
                conn.execute(
                    "DELETE FROM fact_pit_stops WHERE session_key = ?", (session_key,)
                )
                conn.execute(
                    "DELETE FROM fact_race_control WHERE session_key = ?",
                    (session_key,),
                )
                conn.execute(
                    "DELETE FROM fact_intervals WHERE session_key = ?", (session_key,)
                )

                # Iniciar transação atômica (AUDIT-001) para inserção de dados limpos
                conn.execute("BEGIN TRANSACTION")

                # Inserir sessão
                conn.execute(
                    "INSERT INTO dim_sessions SELECT session_key, year, session_name, session_type, circuit_key, circuit_short_name, country_name FROM df_valid"
                )
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
                # Upsert de pilotos usando ON CONFLICT (evita trava de índice e loops de exclusão) - DEC-020
                conn.execute(
                    """
                    INSERT INTO dim_drivers
                    SELECT driver_number, full_name, name_acronym, team_name, country_code FROM df_valid
                    ON CONFLICT (driver_number) DO UPDATE SET
                        full_name = excluded.full_name,
                        name_acronym = excluded.name_acronym,
                        team_name = excluded.team_name,
                        country_code = excluded.country_code
                """
                )
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
                # Reordenar colunas conforme banco
                df_valid["date"] = pd.to_datetime(df_valid["date"], format="ISO8601")
                conn.execute(
                    "INSERT INTO fact_race_control SELECT session_key, driver_number, category, flag, message, date FROM df_valid"
                )
                total_rows_silver += len(df_valid)

        # 6. Processar fact_car_telemetry (Validação Vetorizada de Alta Volumetria)
        tel_file = os.path.join(partition_path, "car_data.parquet")
        if os.path.exists(tel_file):
            df = pd.read_parquet(tel_file)
            total_rows_bronze += len(df)
            df_valid, df_invalid = validate_vectorized_batch(
                df, TELEMETRY_SCHEMA, ["session_key", "driver_number", "date"]
            )
            if not df_invalid.empty:
                quarantine_invalid_rows(
                    df_invalid,
                    "car_data",
                    "Campos chave nulos ou falha de tipo na telemetria",
                    partition_quarantine_path,
                )
                total_rows_quarantine += len(df_invalid)

            if not df_valid.empty:
                # Salvar na Fato
                conn.execute(
                    "INSERT INTO fact_car_telemetry SELECT session_key, driver_number, date, speed, rpm, n_gear, throttle, brake, drs FROM df_valid"
                )
                total_rows_silver += len(df_valid)

        # 7. Processar fact_pit_stops (Validação Vetorizada)
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
                conn.execute(
                    "INSERT INTO fact_pit_stops SELECT session_key, driver_number, lap_number, stop_duration, lane_duration, pit_duration, date FROM df_valid"
                )
                total_rows_silver += len(df_valid)

        # 8. Processar dim_stints (Validação Vetorizada)
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
                conn.execute(
                    "INSERT INTO dim_stints SELECT session_key, driver_number, stint_number, compound, lap_start, lap_end, tyre_age_at_start FROM df_valid"
                )
                total_rows_silver += len(df_valid)

        # 9. Processar dim_weather (Validação Vetorizada)
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
                conn.execute(
                    "INSERT INTO dim_weather SELECT session_key, date, air_temperature, track_temperature, humidity, wind_speed, rainfall FROM df_valid"
                )
                total_rows_silver += len(df_valid)

        # 10. Processar fact_intervals (Validação Vetorizada)
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
                conn.execute(
                    "INSERT INTO fact_intervals SELECT session_key, driver_number, gap_to_leader, interval, date FROM df_valid"
                )
                total_rows_silver += len(df_valid)

        # Gravar a Linhagem de Execução (Audit Trail)
        duration = time.time() - start_time
        conn.execute(
            """
            INSERT INTO fact_pipeline_execution VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now(),
                run_id,
                f"Silver_Pipeline_{gp_dir}_{sess_dir}",
                duration,
                total_rows_bronze,
                total_rows_silver,
                total_rows_quarantine,
                "Success",
            ),
        )

        # Confirmar transação (COMMIT)
        conn.execute("COMMIT")
        print("Transação confirmada (COMMIT) com sucesso no banco temporário.")

    except Exception as e:
        # Se falhar, reverte todas as inserções parciais (ROLLBACK)
        try:
            conn.execute("ROLLBACK")
            print("Transação revertida (ROLLBACK) devido a falha no processamento.")
        except Exception as rollback_err:
            print(f"Erro ao executar ROLLBACK: {rollback_err}")

        # Grava a linhagem de erro (fora da transação desfeita, de forma persistente no arquivo new)
        duration = time.time() - start_time
        try:
            conn.execute(
                """
                INSERT INTO fact_pipeline_execution VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now(),
                    run_id,
                    f"Silver_Pipeline_{gp_dir}_{sess_dir}",
                    duration,
                    total_rows_bronze,
                    0,
                    0,
                    f"Failed: {str(e)[:100]}",
                ),
            )
        except Exception as db_err:
            print(f"Erro ao registrar linhagem de falha no banco: {db_err}")

        # Fecha a conexão e remove o banco temporário corrompido
        conn.close()
        if os.path.exists(SILVER_DB_NEW_PATH):
            os.remove(SILVER_DB_NEW_PATH)
        raise e

    # Fechar conexão de escrita
    conn.close()

    # 11. Substituição Atômica (Hot-Swap) - DEC-015
    try:
        os.replace(SILVER_DB_NEW_PATH, SILVER_DB_PATH)
        print(
            "Hot-Swap executado! Banco de dados principal atualizado de forma atômica."
        )
    except Exception as swap_err:
        if os.path.exists(SILVER_DB_NEW_PATH):
            os.remove(SILVER_DB_NEW_PATH)
        raise OSError(f"Erro crítico no hot-swap dos arquivos do DuckDB: {swap_err}")

    print(
        f"Processamento concluído com sucesso. Bronze: {total_rows_bronze} | Silver: {total_rows_silver} | Quarentena: {total_rows_quarantine} | Tempo: {duration:.2f}s\n"
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
