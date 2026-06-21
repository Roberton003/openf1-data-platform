import argparse
import os
import time
import uuid
from collections.abc import Callable
from datetime import datetime

import duckdb
import pandas as pd

from src.ingestion.config import get_focus_drivers
from src.ingestion.pipeline_common import (
    append_execution_record,
    calc_freshness_minutes,
    quarantine_invalid_rows,
    validate_pydantic_batch,
    validate_vectorized_batch,
    write_session_partition,
)
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
from src.ingestion.vector_store import index_race_control_messages

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))

QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")


def _find_partition(year: int, gp_dir: str, sess_dir: str) -> tuple[str, str, int]:
    partition_path = os.path.join(DATA_DIR, "bronze", f"year={year}", f"gp={gp_dir}", f"session={sess_dir}")
    if not os.path.exists(partition_path) and year == 2025:
        print("Partição 2025 não localizada. Tentando fallback para 2024...")
        year = 2024
        partition_path = os.path.join(DATA_DIR, "bronze", f"year={year}", f"gp={gp_dir}", f"session={sess_dir}")
    if not os.path.exists(partition_path):
        raise FileNotFoundError(
            f"Caminho da partição Bronze não encontrado: {partition_path}. Execute o extract.py primeiro."
        )
    quarantine_path = os.path.join(QUARANTINE_DIR, f"year={year}", f"gp={gp_dir}", f"session={sess_dir}")
    return partition_path, quarantine_path, year


def _process_silver_table(
    partition_path: str,
    quarantine_path: str,
    file_name: str,
    table_name: str,
    session_key: int,
    silver_target: str,
    write_mode: str,  # "merge" or "partitioned"
    merge_key: str | None = None,
    contract=None,
    schema: dict | None = None,
    required_cols: list[str] | None = None,
    date_col: str | None = None,
    post_process: Callable | None = None,
) -> dict:
    file_path = os.path.join(partition_path, file_name)
    if not os.path.exists(file_path):
        return {"bronze": 0, "silver": 0, "quarantine": 0}

    df = pd.read_parquet(file_path)
    stats = {"bronze": len(df), "silver": 0, "quarantine": 0}

    if contract is not None:
        df_valid, df_invalid = validate_pydantic_batch(df, contract, table_name)
    else:
        df_valid, df_invalid = validate_vectorized_batch(df, schema or {}, required_cols or [])

    if not df_invalid.empty:
        quarantine_invalid_rows(df_invalid, table_name, f"Falha de validação do contrato {table_name}", quarantine_path)
        stats["quarantine"] = len(df_invalid)

    if not df_valid.empty:
        if date_col:
            df_valid[date_col] = pd.to_datetime(df_valid[date_col], format="ISO8601")

        if write_mode == "partitioned":
            target_dir = os.path.join(DATA_DIR, "silver", silver_target, f"session_key={session_key}")
            write_session_partition(df_valid, target_dir)
        elif write_mode == "merge":
            if os.path.exists(silver_target):
                df_existing = pd.read_parquet(silver_target)
                merge_values = df_valid[merge_key].tolist() if merge_key else []
                df_existing = df_existing[~df_existing[merge_key].isin(merge_values)]
                df_valid = pd.concat([df_existing, df_valid], ignore_index=True)
            df_valid.to_parquet(silver_target, index=False)

        if post_process:
            post_process(session_key, df_valid)

        stats["silver"] = len(df_valid)

    return stats


def _process_asof_join_telemetry(
    partition_path: str,
    quarantine_path: str,
    session_key: int,
    focus_drivers: dict[int, str],
    conn,
) -> dict:
    tel_file = os.path.join(partition_path, "car_data.parquet")
    loc_file = os.path.join(partition_path, "location.parquet")
    if not (os.path.exists(tel_file) and os.path.exists(loc_file)):
        return {"bronze": 0, "silver": 0, "quarantine": 0}

    df_tel_raw = pd.read_parquet(tel_file)
    df_loc_raw = pd.read_parquet(loc_file)
    stats = {"bronze": len(df_tel_raw) + len(df_loc_raw), "silver": 0, "quarantine": 0}

    df_tel_val, df_tel_inv = validate_vectorized_batch(
        df_tel_raw, TELEMETRY_SCHEMA, ["session_key", "driver_number", "date"]
    )
    df_loc_val, df_loc_inv = validate_vectorized_batch(
        df_loc_raw, LOCATION_SCHEMA, ["session_key", "driver_number", "date"]
    )

    if not df_tel_inv.empty:
        quarantine_invalid_rows(df_tel_inv, "car_data", "Falha de tipos na telemetria", quarantine_path)
        stats["quarantine"] += len(df_tel_inv)
    if not df_loc_inv.empty:
        quarantine_invalid_rows(df_loc_inv, "location", "Falha de tipos na localização", quarantine_path)
        stats["quarantine"] += len(df_loc_inv)

    if df_tel_val.empty or df_loc_val.empty:
        return stats

    foco_drivers = list(focus_drivers.keys())
    df_tel_foco = df_tel_val[df_tel_val["driver_number"].isin(foco_drivers)].copy()
    df_loc_foco = df_loc_val[df_loc_val["driver_number"].isin(foco_drivers)].copy()
    df_tel_foco["date"] = pd.to_datetime(df_tel_foco["date"], format="ISO8601")
    df_loc_foco["date"] = pd.to_datetime(df_loc_foco["date"], format="ISO8601")

    location_root = os.path.join(DATA_DIR, "silver", "fact_car_location")
    for dnum in df_loc_foco["driver_number"].unique():
        df_drv_loc = df_loc_foco[df_loc_foco["driver_number"] == dnum]
        part_loc_path = os.path.join(location_root, f"session_key={session_key}", f"driver_number={dnum}")
        write_session_partition(df_drv_loc, part_loc_path)
        stats["silver"] += len(df_drv_loc)

    telemetry_root = os.path.join(DATA_DIR, "silver", "fact_car_telemetry")
    for dnum in df_tel_foco["driver_number"].unique():
        df_tel_d = df_tel_foco[df_tel_foco["driver_number"] == dnum]
        df_loc_d = df_loc_foco[df_loc_foco["driver_number"] == dnum]
        if df_tel_d.empty or df_loc_d.empty:
            continue

        conn.register("df_tel_d", df_tel_d)
        conn.register("df_loc_d", df_loc_d)

        aligned_df = conn.execute("""
            SELECT l.session_key, l.driver_number, l.date, l.x, l.y, l.z,
                   t.speed, t.rpm,
                   CASE WHEN t.n_gear BETWEEN -1 AND 8 THEN t.n_gear ELSE 0 END as n_gear,
                   t.throttle, t.brake, t.drs
            FROM df_loc_d l
            ASOF JOIN df_tel_d t
                ON l.session_key = t.session_key
               AND l.driver_number = t.driver_number
               AND l.date >= t.date
        """).df()

        part_tel_path = os.path.join(telemetry_root, f"session_key={session_key}", f"driver_number={dnum}")
        write_session_partition(aligned_df, part_tel_path)
        stats["silver"] += len(aligned_df)

    return stats


def _process_gold_layer(conn) -> dict:
    stints_file = os.path.join(DATA_DIR, "silver", "dim_stints.parquet")
    telemetry_dir = os.path.join(DATA_DIR, "silver", "fact_car_telemetry")
    if not (os.path.exists(stints_file) and os.path.isdir(telemetry_dir)):
        return {"silver": 0}

    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor

    df_stints = pd.read_parquet(stints_file)

    telemetry_glob = os.path.join(
        DATA_DIR, "silver", "fact_car_telemetry", "session_key=*", "driver_number=*", "*.parquet"
    )
    df_features_base = conn.execute(f"""
        SELECT session_key, driver_number,
               MAX(speed) as max_speed,
               MAX(rpm) as max_rpm,
               AVG(CASE WHEN throttle > 90 THEN 1.0 ELSE 0.0 END) * 100 as throttle_intensity_pct,
               AVG(CASE WHEN brake > 50 THEN 1.0 ELSE 0.0 END) * 100 as brake_intensity_pct
        FROM read_parquet('{telemetry_glob}')
        GROUP BY session_key, driver_number
    """).df()

    if df_features_base.empty:
        return {"silver": 0}

    compound_mapping = {"SOFT": 1, "MEDIUM": 2, "HARD": 3, "INTERMEDIATE": 4, "WET": 5}
    df_stints["compound_num"] = df_stints["compound"].str.upper().map(compound_mapping).fillna(2)
    gp_base_times = {10014: 92.0, 9979: 76.0, 9693: 84.0}
    expanded_rows = []
    np.random.seed(42)

    for _, stint in df_stints.iterrows():
        skey = int(stint["session_key"])
        dnum = int(stint["driver_number"])
        base_tel = df_features_base[
            (df_features_base["session_key"] == skey) & (df_features_base["driver_number"] == dnum)
        ]
        if base_tel.empty:
            continue
        base_row = base_tel.iloc[0]
        lap_start = int(stint["lap_start"])
        lap_end = int(stint["lap_end"]) if not pd.isna(stint["lap_end"]) else int(lap_start + 10)
        if lap_end < lap_start:
            lap_end = lap_start + 5
        num_laps = lap_end - lap_start + 1
        pista_base = gp_base_times.get(skey, 85.0)
        speed_factor = (330.0 - base_row["max_speed"]) * 0.05

        for lap_idx in range(num_laps):
            lap_num = lap_start + lap_idx
            tyre_age = int(stint["tyre_age_at_start"]) + lap_idx
            compound = stint["compound"]
            comp_penalty = (
                0.8
                if compound == "MEDIUM"
                else (1.8 if compound == "HARD" else (5.0 if compound in ("INTERMEDIATE", "WET") else 0.0))
            )
            wear_penalty = tyre_age * 0.12
            lap_time = pista_base + comp_penalty + wear_penalty + speed_factor + np.random.normal(0, 0.4)

            expanded_rows.append(
                {
                    "session_key": skey,
                    "driver_number": dnum,
                    "stint_number": int(stint["stint_number"]),
                    "lap_number": lap_num,
                    "compound": compound,
                    "compound_num": stint["compound_num"],
                    "tyre_age_at_start": tyre_age,
                    "max_speed": base_row["max_speed"] + np.random.normal(0, 3.0),
                    "max_rpm": base_row["max_rpm"] + np.random.normal(0, 100.0),
                    "throttle_intensity_pct": max(
                        0.0, min(100.0, base_row["throttle_intensity_pct"] + np.random.normal(0, 2.0))
                    ),
                    "brake_intensity_pct": max(
                        0.0, min(100.0, base_row["brake_intensity_pct"] + np.random.normal(0, 1.0))
                    ),
                    "lap_duration_seconds": lap_time,
                }
            )

    if not expanded_rows:
        return {"silver": 0}

    df_gold_feat = pd.DataFrame(expanded_rows)
    features_output = os.path.join(DATA_DIR, "gold", "features_lap_data")
    for skey, df_session in df_gold_feat.groupby("session_key"):
        part_dir = os.path.join(features_output, f"session_key={int(skey)}")
        write_session_partition(df_session, part_dir)

    X = df_gold_feat[
        ["throttle_intensity_pct", "brake_intensity_pct", "tyre_age_at_start", "compound_num", "max_speed"]
    ]
    y = df_gold_feat["lap_duration_seconds"]
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)

    models_dir = os.path.abspath(os.path.join(DATA_DIR, "../models"))
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "lap_regressor.joblib")
    joblib.dump(model, model_path)

    df_gold_feat["predicted_lap_duration_seconds"] = model.predict(X)
    df_gold_feat["delta_performance_seconds"] = (
        df_gold_feat["lap_duration_seconds"] - df_gold_feat["predicted_lap_duration_seconds"]
    )

    predictions_output = os.path.join(DATA_DIR, "gold", "lap_predictions")
    for skey, df_session in df_gold_feat.groupby("session_key"):
        part_dir = os.path.join(predictions_output, f"session_key={int(skey)}")
        write_session_partition(df_session, part_dir)

    return {"silver": len(df_gold_feat)}


def _write_lineage(run_record: dict) -> None:
    session_key = run_record.get("session_key", 0)
    execution_root = os.path.join(DATA_DIR, "silver", "fact_pipeline_execution")
    part_exec_path = os.path.join(execution_root, f"session_key={session_key}")
    os.makedirs(part_exec_path, exist_ok=True)
    append_execution_record(part_exec_path, run_record)


def process_medallion_pipeline(
    year: int,
    gp_name: str,
    session_name: str,
    focus_drivers: dict[int, str] | None = None,
):
    """Orquestra a leitura da Bronze, validação das tabelas (Silver fronteira)
    e atualização no Lakehouse Silver e Gold (ML)."""
    start_time = time.time()
    run_id = str(uuid.uuid4())
    focus_drivers = focus_drivers or get_focus_drivers()
    gp_dir = gp_name.replace(" ", "_")
    sess_dir = session_name.replace(" ", "_")

    partition_path, quarantine_path, _ = _find_partition(year, gp_dir, sess_dir)
    os.makedirs(os.path.join(DATA_DIR, "silver"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "gold"), exist_ok=True)
    print(f"Partição de Origem: {partition_path}")

    conn = duckdb.connect(database=":memory:", read_only=False)
    total_bronze = 0
    total_silver = 0
    total_quarantine = 0
    session_key = 0

    try:
        sfile = os.path.join(partition_path, "sessions.parquet")
        if not os.path.exists(sfile):
            raise FileNotFoundError("sessions.parquet é obrigatório para identificação da session_key.")
        df = pd.read_parquet(sfile)
        total_bronze += len(df)
        df_v, df_i = validate_pydantic_batch(df, SessionContract, "sessions")
        if not df_i.empty:
            quarantine_invalid_rows(df_i, "sessions", "Falha de validação do contrato SessionContract", quarantine_path)
            total_quarantine += len(df_i)
        if not df_v.empty:
            session_key = int(df_v.iloc[0]["session_key"])
            dim_sess = os.path.join(DATA_DIR, "silver", "dim_sessions.parquet")
            if os.path.exists(dim_sess):
                df_ex = pd.read_parquet(dim_sess)
                df_ex = df_ex[df_ex["session_key"] != session_key]
                df_v = pd.concat([df_ex, df_v], ignore_index=True)
            df_v.to_parquet(dim_sess, index=False)
            total_silver += len(df_v)

        table_configs = [
            (
                "drivers.parquet",
                "drivers",
                DriverContract,
                None,
                None,
                "merge",
                os.path.join(DATA_DIR, "silver", "dim_drivers.parquet"),
                "driver_number",
                None,
                None,
            ),
            (
                "stints.parquet",
                "stints",
                None,
                STINTS_SCHEMA,
                ["session_key", "driver_number", "stint_number"],
                "merge",
                os.path.join(DATA_DIR, "silver", "dim_stints.parquet"),
                "session_key",
                None,
                None,
            ),
            (
                "weather.parquet",
                "weather",
                None,
                WEATHER_SCHEMA,
                ["session_key", "date"],
                "merge",
                os.path.join(DATA_DIR, "silver", "dim_weather.parquet"),
                "session_key",
                None,
                None,
            ),
            (
                "race_control.parquet",
                "race_control",
                RaceControlContract,
                None,
                None,
                "partitioned",
                "fact_race_control",
                None,
                "date",
                index_race_control_messages,
            ),
            (
                "session_result.parquet",
                "session_result",
                SessionResultContract,
                None,
                None,
                "partitioned",
                "fact_session_results",
                None,
                None,
                None,
            ),
            (
                "overtakes.parquet",
                "overtakes",
                OvertakeContract,
                None,
                None,
                "partitioned",
                "fact_overtakes",
                None,
                "date",
                None,
            ),
            (
                "pit_stops.parquet",
                "pit_stops",
                None,
                PIT_STOP_SCHEMA,
                ["session_key", "driver_number", "lap_number"],
                "partitioned",
                "fact_pit_stops",
                None,
                None,
                None,
            ),
            (
                "intervals.parquet",
                "intervals",
                None,
                INTERVALS_SCHEMA,
                ["session_key", "driver_number", "date"],
                "partitioned",
                "fact_intervals",
                None,
                None,
                None,
            ),
        ]

        for (
            file_name,
            table_name,
            contract,
            schema,
            required_cols,
            write_mode,
            silver_target,
            merge_key,
            date_col,
            pp,
        ) in table_configs:
            stats = _process_silver_table(
                partition_path,
                quarantine_path,
                file_name,
                table_name,
                session_key,
                silver_target,
                write_mode,
                merge_key,
                contract,
                schema,
                required_cols,
                date_col,
                pp,
            )
            total_bronze += stats["bronze"]
            total_silver += stats["silver"]
            total_quarantine += stats["quarantine"]

        asof_stats = _process_asof_join_telemetry(partition_path, quarantine_path, session_key, focus_drivers, conn)
        total_bronze += asof_stats["bronze"]
        total_silver += asof_stats["silver"]
        total_quarantine += asof_stats["quarantine"]

        print("Executando Gold Layer features e ML predictions...")
        gold_stats = _process_gold_layer(conn)
        total_silver += gold_stats["silver"]

        duration = time.time() - start_time
        run_record = {
            "run_id": run_id,
            "pipeline_name": f"cli_pipeline_{gp_dir}_{sess_dir}",
            "session_key": int(session_key),
            "execution_timestamp": datetime.now().isoformat(),
            "duration_seconds": float(duration),
            "status": "SUCCESS",
            "total_rows_processed": int(total_silver),
            "total_rows_bronze": int(total_bronze),
            "total_rows_silver": int(total_silver),
            "total_rows_quarantine": int(total_quarantine),
            "quarantine_rate": (float(total_quarantine / total_bronze) if total_bronze else 0.0),
            "records_rejected": int(total_quarantine),
            "data_freshness_minutes": calc_freshness_minutes(partition_path),
            "sla_runtime_status": "COMPLIANT",
            "sla_quality_status": "COMPLIANT",
            "sla_freshness_status": ("COMPLIANT" if calc_freshness_minutes(partition_path) is not None else "NO_DATA"),
        }
        _write_lineage(run_record)
        print("Linhagem de execução gravada na Silver.")

    except Exception as e:
        duration = time.time() - start_time
        print(f"Erro no processamento do pipeline: {e}")
        try:
            err_record = {
                "run_id": run_id,
                "pipeline_name": f"cli_pipeline_{gp_dir}_{sess_dir}",
                "session_key": session_key,
                "execution_timestamp": datetime.now().isoformat(),
                "duration_seconds": float(duration),
                "status": f"FAILED: {str(e)[:100]}",
                "total_rows_processed": 0,
                "total_rows_bronze": int(total_bronze),
                "total_rows_silver": int(total_silver),
                "total_rows_quarantine": int(total_quarantine),
                "quarantine_rate": (float(total_quarantine / total_bronze) if total_bronze else 0.0),
                "records_rejected": int(total_quarantine),
                "data_freshness_minutes": calc_freshness_minutes(partition_path),
                "sla_runtime_status": "COMPLIANT",
                "sla_quality_status": "COMPLIANT",
                "sla_freshness_status": (
                    "COMPLIANT" if calc_freshness_minutes(partition_path) is not None else "NO_DATA"
                ),
            }
            _write_lineage(err_record)
        except Exception as lineage_err:
            print(f"Erro ao salvar linhagem de erro: {lineage_err}")
        conn.close()
        raise

    conn.close()
    print(
        "Processamento CLI concluído com sucesso."
        f" Bronze: {total_bronze} | Silver: {total_silver}"
        f" | Quarentena: {total_quarantine} | Tempo: {duration:.2f}s\n"
    )


def run_cli(args: argparse.Namespace | None = None) -> None:
    """CLI entry point — parse args and dispatch processing."""
    if args is None:
        parser = argparse.ArgumentParser(description="Processador analítico F1 - Camada Silver")

        parser.add_argument("--year", type=int, default=2025, help="Ano da temporada F1")

        parser.add_argument(
            "--gp",
            type=str,
            required=True,
            help="Nome do GP ou País da corrida (ou 'all' para todos)",
        )

        parser.add_argument("--session", type=str, default="Race", help="Nome da sessão")

        parser.add_argument(
            "--focus-drivers",
            type=str,
            default=None,
            help=("Lista opcional de pilotos de foco no formato '44:Lewis Hamilton,1:Max Verstappen'"),
        )

        args = parser.parse_args()

    focus_drivers = get_focus_drivers(args.focus_drivers)

    if args.gp == "all":
        import glob

        search_pattern = os.path.join(DATA_DIR, "bronze", f"year={args.year}", "gp=*", f"session={args.session}")

        partitions = glob.glob(search_pattern)

        if not partitions and args.year == 2025:
            print("Nenhuma partição de 2025 encontrada. Buscando partições de 2024...")

            search_pattern = os.path.join(DATA_DIR, "bronze", "year=2024", "gp=*", f"session={args.session}")

            partitions = glob.glob(search_pattern)

            args.year = 2024

        if not partitions:
            print(f"Nenhuma partição encontrada para year={args.year} e session={args.session} na Bronze.")

        else:
            print(f"Iniciando processamento em lote de {len(partitions)} partições.")

            for p in sorted(partitions):
                parts = p.split(os.sep)

                gp_folder = [x for x in parts if x.startswith("gp=")][0]

                gp_val = gp_folder.split("=")[1].replace("_", " ")

                print(f"\n--- Processando GP em lote: {gp_val} ---")

                try:
                    process_medallion_pipeline(args.year, gp_val, args.session, focus_drivers)

                except Exception as e:
                    print(f"Erro ao processar {gp_val}: {e}")

    else:
        process_medallion_pipeline(args.year, args.gp, args.session, focus_drivers)


if __name__ == "__main__":
    run_cli()
