import os
import time

import duckdb
import joblib
import pandas as pd
import requests
from dagster import AssetExecutionContext, asset
from sklearn.ensemble import RandomForestRegressor
from tenacity import retry, stop_after_attempt, wait_exponential

from src.ingestion.config import PILOTOS_FOCO

# Reutilizar esquemas e contratos de validação
from src.ingestion.schemas import (
    DriverContract,
    OvertakeContract,
    RaceControlContract,
    SessionContract,
    SessionResultContract,
)

BASE_URL = "https://api.openf1.org/v1"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))

# GPs Estratégicos Selecionados (ADR 003)
SESSIONS_TO_PROCESS = [
    {"year": 2025, "session_key": 10014, "gp": "Bahrain"},
    {"year": 2025, "session_key": 9979, "gp": "Monaco"},
    {"year": 2025, "session_key": 9693, "gp": "Australia"},
]


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=2, max=15))
def fetch_api(endpoint: str, params: dict = None) -> list:
    """
    Consome a API pública do OpenF1 de forma resiliente com retentativas automáticas.
    """
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return []
        raise e
    except requests.exceptions.RequestException as e:
        raise e


# =====================================================================
# 1. CAMADA BRONZE: ASSETS DE INGESTÃO (Raw Parquet)
# =====================================================================


@asset(group_name="Camada_Bronze")
def bronze_sessions(context: AssetExecutionContext) -> None:
    """
    Extrai as sessões brutas de 2025/2024 para os GPs especificados.
    """
    os.makedirs(os.path.join(DATA_DIR, "bronze"), exist_ok=True)
    all_sess = []
    for gp_cfg in SESSIONS_TO_PROCESS:
        context.log.info(
            f"Ingerindo metadado de sessão para GP {gp_cfg['gp']} ({gp_cfg['session_key']})"
        )
        data = fetch_api("sessions", {"session_key": gp_cfg["session_key"]})
        if data:
            all_sess.extend(data)
            time.sleep(1.0)

    if all_sess:
        df = pd.DataFrame(all_sess)
        output_file = os.path.join(DATA_DIR, "bronze", "sessions.parquet")
        df.to_parquet(output_file, index=False)
        context.log.info(f"Salvas {len(df)} sessões brutas em {output_file}")


@asset(group_name="Camada_Bronze", deps=[bronze_sessions])
def bronze_drivers(context: AssetExecutionContext) -> None:
    """
    Extrai os dados brutos de pilotos para os GPs de foco.
    """
    all_drivers = []
    for gp_cfg in SESSIONS_TO_PROCESS:
        context.log.info(f"Ingerindo pilotos para session_key {gp_cfg['session_key']}")
        data = fetch_api("drivers", {"session_key": gp_cfg["session_key"]})
        if data:
            all_drivers.extend(data)
            time.sleep(1.0)

    if all_drivers:
        df = pd.DataFrame(all_drivers).drop_duplicates(
            subset=["driver_number", "session_key"]
        )
        output_file = os.path.join(DATA_DIR, "bronze", "drivers.parquet")
        df.to_parquet(output_file, index=False)
        context.log.info(f"Salvos {len(df)} pilotos brutos em {output_file}")


@asset(group_name="Camada_Bronze", deps=[bronze_sessions])
def bronze_race_control_and_stints(context: AssetExecutionContext) -> None:
    """
    Ingere metadados de Race Control, Stints de Pneu e Pit Stops para os 3 GPs.
    """
    for gp_cfg in SESSIONS_TO_PROCESS:
        skey = gp_cfg["session_key"]
        gp_name = gp_cfg["gp"]
        context.log.info(
            f"Ingerindo Stints, Pits e Race Control para {gp_name} ({skey})"
        )

        # 1. Stints
        stints = fetch_api("stints", {"session_key": skey})
        if stints:
            os.makedirs(
                os.path.join(DATA_DIR, "bronze", f"session_key={skey}"), exist_ok=True
            )
            pd.DataFrame(stints).to_parquet(
                os.path.join(
                    DATA_DIR, "bronze", f"session_key={skey}", "stints.parquet"
                ),
                index=False,
            )

        # 2. Pit Stops
        pits = fetch_api("pit", {"session_key": skey})
        if pits:
            pd.DataFrame(pits).to_parquet(
                os.path.join(
                    DATA_DIR, "bronze", f"session_key={skey}", "pit_stops.parquet"
                ),
                index=False,
            )

        # 3. Race Control
        rc = fetch_api("race_control", {"session_key": skey})
        if rc:
            pd.DataFrame(rc).to_parquet(
                os.path.join(
                    DATA_DIR, "bronze", f"session_key={skey}", "race_control.parquet"
                ),
                index=False,
            )

        # 4. Weather
        weather = fetch_api("weather", {"session_key": skey})
        if weather:
            pd.DataFrame(weather).to_parquet(
                os.path.join(
                    DATA_DIR, "bronze", f"session_key={skey}", "weather.parquet"
                ),
                index=False,
            )

        # 5. Session Results
        res = fetch_api("session_result", {"session_key": skey})
        if res:
            df_res = pd.DataFrame(res)
            # Cast de colunas com tipos mistos para evitar inconsistências no PyArrow
            for col in ["gap_to_leader", "interval"]:
                if col in df_res.columns:
                    df_res[col] = df_res[col].astype(str)
            df_res.to_parquet(
                os.path.join(
                    DATA_DIR, "bronze", f"session_key={skey}", "session_result.parquet"
                ),
                index=False,
            )

        # 6. Overtakes
        ov = fetch_api("overtakes", {"session_key": skey})
        if ov:
            df_ov = pd.DataFrame(ov)
            df_ov.to_parquet(
                os.path.join(
                    DATA_DIR, "bronze", f"session_key={skey}", "overtakes.parquet"
                ),
                index=False,
            )

        time.sleep(1.0)


@asset(group_name="Camada_Bronze", deps=[bronze_drivers])
def bronze_telemetry_spatial(context: AssetExecutionContext) -> None:
    """
    Extrai telemetria (car_data) e localização física da pista para os pilotos dos 3 GPs selecionados.
    """
    # Lendo pilotos mapeados para saber quem baixar
    drivers_file = os.path.join(DATA_DIR, "bronze", "drivers.parquet")
    if not os.path.exists(drivers_file):
        context.log.warn("Arquivo de pilotos brutos ausente. Abortando telemetria.")
        return

    df_drv = pd.read_parquet(drivers_file)

    for gp_cfg in SESSIONS_TO_PROCESS:
        skey = gp_cfg["session_key"]
        gp_name = gp_cfg["gp"]

        # Pegar apenas os pilotos registrados nesta sessão
        drivers_in_session = df_drv[df_drv["session_key"] == skey][
            "driver_number"
        ].tolist()

        # Para evitar estourar a API com requisições simultâneas de todos os 20 pilotos,
        # vamos limitar a telemetria aos 5 pilotos de foco histórico do projeto (reduz tempo e garante estabilidade)
        foco_drivers = list(PILOTOS_FOCO.keys())
        active_drivers = [d for d in drivers_in_session if d in foco_drivers]

        # Garante que criamos a pasta da partição
        os.makedirs(
            os.path.join(DATA_DIR, "bronze", f"session_key={skey}"), exist_ok=True
        )

        for dnum in active_drivers:
            context.log.info(
                f"Ingerindo dados espaciais e telemetria para GP {gp_name} - Piloto #{dnum}"
            )
            params = {"session_key": skey, "driver_number": dnum}

            # 1. Telemetria
            tel_data = fetch_api("car_data", params)
            if tel_data:
                pd.DataFrame(tel_data).to_parquet(
                    os.path.join(
                        DATA_DIR,
                        "bronze",
                        f"session_key={skey}",
                        f"car_data_{dnum}.parquet",
                    ),
                    index=False,
                )

            # 2. Localização
            loc_data = fetch_api("location", params)
            if loc_data:
                df_loc = pd.DataFrame(loc_data)
                # Cast de coordenadas
                for col in ["x", "y", "z"]:
                    if col in df_loc.columns:
                        df_loc[col] = (
                            pd.to_numeric(df_loc[col], errors="coerce")
                            .fillna(0)
                            .astype(int)
                        )
                df_loc.to_parquet(
                    os.path.join(
                        DATA_DIR,
                        "bronze",
                        f"session_key={skey}",
                        f"location_{dnum}.parquet",
                    ),
                    index=False,
                )

            # 3. Intervals
            int_data = fetch_api("intervals", params)
            if int_data:
                df_int = pd.DataFrame(int_data)
                for col in ["gap_to_leader", "interval"]:
                    if col in df_int.columns:
                        df_int[col] = df_int[col].astype(str)
                df_int.to_parquet(
                    os.path.join(
                        DATA_DIR,
                        "bronze",
                        f"session_key={skey}",
                        f"intervals_{dnum}.parquet",
                    ),
                    index=False,
                )

            time.sleep(1.5)


# =====================================================================
# 2. CAMADA SILVER: ASSETS DE QUALIDADE E HIGH-PERFORMANCE ALIGNMENT (ASOF JOIN)
# =====================================================================


@asset(group_name="Camada_Silver", deps=[bronze_sessions])
def silver_sessions(context: AssetExecutionContext) -> None:
    """
    Valida e formata as sessões analíticas para a camada Silver (Parquet).
    """
    src = os.path.join(DATA_DIR, "bronze", "sessions.parquet")
    if not os.path.exists(src):
        return

    df = pd.read_parquet(src)
    valid_records = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        try:
            SessionContract(**row_dict)
            valid_records.append(row_dict)
        except Exception as e:
            context.log.warn(
                f"Sessão {row_dict.get('session_key')} falhou no contrato: {e}"
            )

    if valid_records:
        os.makedirs(os.path.join(DATA_DIR, "silver"), exist_ok=True)
        pd.DataFrame(valid_records).to_parquet(
            os.path.join(DATA_DIR, "silver", "dim_sessions.parquet"), index=False
        )
        context.log.info("Sessões gravadas na Silver.")


@asset(group_name="Camada_Silver", deps=[bronze_drivers])
def silver_drivers(context: AssetExecutionContext) -> None:
    """
    Valida e formata a lista de pilotos (Parquet).
    """
    src = os.path.join(DATA_DIR, "bronze", "drivers.parquet")
    if not os.path.exists(src):
        return

    df = pd.read_parquet(src)
    valid_records = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        try:
            DriverContract(**row_dict)
            valid_records.append(row_dict)
        except Exception as e:
            context.log.warn(
                f"Piloto {row_dict.get('driver_number')} falhou no contrato: {e}"
            )

    if valid_records:
        df_valid = pd.DataFrame(valid_records).drop_duplicates(subset=["driver_number"])
        pd.DataFrame(df_valid).to_parquet(
            os.path.join(DATA_DIR, "silver", "dim_drivers.parquet"), index=False
        )
        context.log.info("Pilotos gravados na Silver.")


@asset(group_name="Camada_Silver", deps=[bronze_race_control_and_stints])
def silver_metadata_tables(context: AssetExecutionContext) -> None:
    """
    Valida e transiciona clima, pit stops, stints, race control, resultados e ultrapassagens para o Lakehouse Silver.
    """
    os.makedirs(os.path.join(DATA_DIR, "silver"), exist_ok=True)

    stints_all = []
    weather_all = []
    pits_all = []
    rc_all = []
    res_all = []
    ov_all = []

    for gp_cfg in SESSIONS_TO_PROCESS:
        skey = gp_cfg["session_key"]
        base_path = os.path.join(DATA_DIR, "bronze", f"session_key={skey}")
        if not os.path.exists(base_path):
            continue

        # 1. Stints
        sf = os.path.join(base_path, "stints.parquet")
        if os.path.exists(sf):
            st_df = pd.read_parquet(sf)
            st_df["session_key"] = st_df["session_key"].astype(int)
            st_df["driver_number"] = st_df["driver_number"].astype(int)
            stints_all.append(st_df)

        # 2. Weather
        wf = os.path.join(base_path, "weather.parquet")
        if os.path.exists(wf):
            w_df = pd.read_parquet(wf)
            w_df["session_key"] = w_df["session_key"].astype(int)
            w_df["date"] = pd.to_datetime(w_df["date"], format="ISO8601")
            weather_all.append(w_df)

        # 3. Pit Stops
        pf = os.path.join(base_path, "pit_stops.parquet")
        if os.path.exists(pf):
            p_df = pd.read_parquet(pf)
            p_df["session_key"] = p_df["session_key"].astype(int)
            p_df["driver_number"] = p_df["driver_number"].astype(int)
            pits_all.append(p_df)

        # 4. Race Control
        rcf = os.path.join(base_path, "race_control.parquet")
        if os.path.exists(rcf):
            rc_df = pd.read_parquet(rcf)
            rc_df["session_key"] = rc_df["session_key"].astype(int)
            rc_df["date"] = pd.to_datetime(rc_df["date"], format="ISO8601")
            rc_all.append(rc_df)

        # 5. Session Results
        res_f = os.path.join(base_path, "session_result.parquet")
        if os.path.exists(res_f):
            res_df = pd.read_parquet(res_f)
            res_df["session_key"] = res_df["session_key"].astype(int)
            res_df["driver_number"] = res_df["driver_number"].astype(int)
            res_all.append(res_df)

        # 6. Overtakes
        ov_f = os.path.join(base_path, "overtakes.parquet")
        if os.path.exists(ov_f):
            ov_df = pd.read_parquet(ov_f)
            ov_df["session_key"] = ov_df["session_key"].astype(int)
            ov_df["overtaking_driver_number"] = ov_df[
                "overtaking_driver_number"
            ].astype(int)
            ov_df["overtaken_driver_number"] = ov_df["overtaken_driver_number"].astype(
                int
            )
            ov_df["date"] = pd.to_datetime(ov_df["date"], format="ISO8601")
            ov_all.append(ov_df)

    import shutil

    # Salvar consolidados (Dimensões)
    if stints_all:
        pd.concat(stints_all).to_parquet(
            os.path.join(DATA_DIR, "silver", "dim_stints.parquet"), index=False
        )
    if weather_all:
        pd.concat(weather_all).to_parquet(
            os.path.join(DATA_DIR, "silver", "dim_weather.parquet"), index=False
        )

    # Salvar particionados (Fatos)
    if pits_all:
        pits_df = pd.concat(pits_all)
        target = os.path.join(DATA_DIR, "silver", "fact_pit_stops")
        shutil.rmtree(target, ignore_errors=True)
        pits_df.to_parquet(target, partition_cols=["session_key"], index=False)

    if rc_all:
        # Validar via contrato Pydantic para logs de race control
        df_rc = pd.concat(rc_all)
        valid_rc = []
        for _, r in df_rc.iterrows():
            r_dict = r.to_dict()
            if isinstance(r_dict["date"], pd.Timestamp):
                r_dict["date"] = r_dict["date"].to_pydatetime()
            try:
                # Tratar chaves nulas do piloto antes de validar
                if pd.isna(r_dict.get("driver_number")):
                    r_dict["driver_number"] = None
                RaceControlContract(**r_dict)
                valid_rc.append(r_dict)
            except Exception:
                pass
        if valid_rc:
            rc_df = pd.DataFrame(valid_rc)
            target = os.path.join(DATA_DIR, "silver", "fact_race_control")
            shutil.rmtree(target, ignore_errors=True)
            rc_df.to_parquet(target, partition_cols=["session_key"], index=False)

    if res_all:
        # Validar via contrato Pydantic para resultados de sessão
        df_res = pd.concat(res_all)
        valid_res = []
        for _, r in df_res.iterrows():
            r_dict = r.to_dict()
            if pd.isna(r_dict.get("position")):
                r_dict["position"] = None
            else:
                r_dict["position"] = int(r_dict["position"])

            r_dict["session_key"] = int(r_dict["session_key"])
            r_dict["driver_number"] = int(r_dict["driver_number"])

            for k in [
                "number_of_laps",
                "points",
                "dnf",
                "dns",
                "dsq",
                "duration",
                "gap_to_leader",
            ]:
                if k in r_dict:
                    if pd.isna(r_dict[k]):
                        r_dict[k] = None
                    elif k in ["dnf", "dns", "dsq"]:
                        r_dict[k] = bool(r_dict[k])
                    elif k in ["number_of_laps"]:
                        r_dict[k] = int(r_dict[k])
                    elif k in ["points", "duration"]:
                        r_dict[k] = float(r_dict[k])
            try:
                SessionResultContract(**r_dict)
                valid_res.append(r_dict)
            except Exception:
                pass
        if valid_res:
            res_df = pd.DataFrame(valid_res)
            target = os.path.join(DATA_DIR, "silver", "fact_session_results")
            shutil.rmtree(target, ignore_errors=True)
            res_df.to_parquet(target, partition_cols=["session_key"], index=False)

    if ov_all:
        # Validar via contrato Pydantic para ultrapassagens
        df_ov = pd.concat(ov_all)
        valid_ov = []
        for _, r in df_ov.iterrows():
            r_dict = r.to_dict()
            if isinstance(r_dict["date"], pd.Timestamp):
                r_dict["date"] = r_dict["date"].to_pydatetime()
            r_dict["session_key"] = int(r_dict["session_key"])
            r_dict["overtaking_driver_number"] = int(r_dict["overtaking_driver_number"])
            r_dict["overtaken_driver_number"] = int(r_dict["overtaken_driver_number"])
            if pd.isna(r_dict.get("position")):
                r_dict["position"] = 0
            else:
                r_dict["position"] = int(r_dict["position"])
            try:
                OvertakeContract(**r_dict)
                valid_ov.append(r_dict)
            except Exception:
                pass
        if valid_ov:
            ov_df = pd.DataFrame(valid_ov)
            target = os.path.join(DATA_DIR, "silver", "fact_overtakes")
            shutil.rmtree(target, ignore_errors=True)
            ov_df.to_parquet(target, partition_cols=["session_key"], index=False)


@asset(group_name="Camada_Silver", deps=[bronze_telemetry_spatial])
def silver_telemetry_location_aligned(context: AssetExecutionContext) -> None:
    """
    Lê a telemetria e localização espacial da Bronze, executa o ASOF JOIN analítico e
    salva os arquivos Parquet particionados na Silver (desacoplamento total de storage e compute).
    """
    start_time = time.time()
    # Conexão DuckDB temporária na memória
    conn = duckdb.connect(database=":memory:", read_only=False)

    # Criar pastas para datasets particionados
    telemetry_root = os.path.join(DATA_DIR, "silver", "fact_car_telemetry")
    location_root = os.path.join(DATA_DIR, "silver", "fact_car_location")
    os.makedirs(telemetry_root, exist_ok=True)
    os.makedirs(location_root, exist_ok=True)

    foco_drivers = list(PILOTOS_FOCO.keys())

    for gp_cfg in SESSIONS_TO_PROCESS:
        skey = gp_cfg["session_key"]
        base_path = os.path.join(DATA_DIR, "bronze", f"session_key={skey}")
        if not os.path.exists(base_path):
            continue

        for dnum in foco_drivers:
            t_file = os.path.join(base_path, f"car_data_{dnum}.parquet")
            l_file = os.path.join(base_path, f"location_{dnum}.parquet")

            if os.path.exists(t_file) and os.path.exists(l_file):
                context.log.info(
                    f"Alinhando dados espaciais via ASOF JOIN para session_key {skey} - Piloto #{dnum}"
                )

                # Registrar tabelas do Pandas temporariamente
                df_tel = pd.read_parquet(t_file)
                df_loc = pd.read_parquet(l_file)

                # Garantir tipos e conversões
                df_tel["date"] = pd.to_datetime(df_tel["date"], format="ISO8601")
                df_loc["date"] = pd.to_datetime(df_loc["date"], format="ISO8601")

                # Executar ASOF JOIN no DuckDB analítico
                # Alinha a telemetria e a localização espacial
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
                    FROM df_loc l
                    ASOF JOIN df_tel t 
                        ON l.session_key = t.session_key 
                       AND l.driver_number = t.driver_number 
                       AND l.date >= t.date
                    """
                ).df()

                # Salvar de forma particionada
                part_tel_path = os.path.join(
                    telemetry_root, f"session_key={skey}", f"driver_number={dnum}"
                )
                os.makedirs(part_tel_path, exist_ok=True)
                aligned_df.to_parquet(
                    os.path.join(part_tel_path, "data.parquet"), index=False
                )

                # Também salvamos a localização Silver isolada particionada
                part_loc_path = os.path.join(
                    location_root, f"session_key={skey}", f"driver_number={dnum}"
                )
                os.makedirs(part_loc_path, exist_ok=True)
                df_loc.to_parquet(
                    os.path.join(part_loc_path, "data.parquet"), index=False
                )

    context.log.info("ASOF JOINs analíticos gravados na Silver com sucesso.")

    # Registrar linhagem em fact_pipeline_execution
    import uuid
    from datetime import datetime

    execution_root = os.path.join(DATA_DIR, "silver", "fact_pipeline_execution")
    os.makedirs(execution_root, exist_ok=True)

    for gp_cfg in SESSIONS_TO_PROCESS:
        skey = gp_cfg["session_key"]
        run_record = {
            "run_id": str(uuid.uuid4()),
            "pipeline_name": "dagster",
            "session_key": int(skey),
            "execution_timestamp": datetime.now().isoformat(),
            "duration_seconds": float(time.time() - start_time),
            "status": "SUCCESS",
            "total_rows_processed": 0,
        }

        part_exec_path = os.path.join(execution_root, f"session_key={skey}")
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


# =====================================================================
# 3. CAMADA GOLD: FEATURE ENGINEERING, MODELAGEM IA & PREDICÕES (MLOps)
# =====================================================================


@asset(
    group_name="Camada_Gold",
    deps=[silver_telemetry_location_aligned, silver_metadata_tables],
)
def gold_feature_engineering_lap_data(context: AssetExecutionContext) -> None:
    """
    Agrega a telemetria física Silver em nível de volta simulada para criar o Feature Store de treinamento de IA.
    """
    import numpy as np

    os.makedirs(os.path.join(DATA_DIR, "gold"), exist_ok=True)

    stints_file = os.path.join(DATA_DIR, "silver", "dim_stints.parquet")
    telemetry_root = os.path.join(DATA_DIR, "silver", "fact_car_telemetry")

    if not os.path.exists(stints_file) or not os.path.exists(telemetry_root):
        context.log.warn("Dados Silver insuficientes para engenharia de features.")
        return

    df_stints = pd.read_parquet(stints_file)
    conn = duckdb.connect(database=":memory:", read_only=False)

    # Obter agregação de telemetria base por piloto e GP
    query = """
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
    df_features_base = conn.execute(query).df()

    # Mapeamento de composto de pneu
    compound_mapping = {"SOFT": 1, "MEDIUM": 2, "HARD": 3, "INTERMEDIATE": 4, "WET": 5}
    df_stints["compound_num"] = (
        df_stints["compound"].str.upper().map(compound_mapping).fillna(2)
    )

    # Tempos base de voltas por session_key (Bahrain 10014 = 92s, Monaco 9979 = 76s, Australia 9693 = 84s)
    gp_base_times = {10014: 92.0, 9979: 76.0, 9693: 84.0}

    # Expandir cada stint em voltas individuais para preencher o Feature Store
    expanded_rows = []
    np.random.seed(42)  # Garantir reprodutibilidade

    for _, stint in df_stints.iterrows():
        skey = int(stint["session_key"])
        dnum = int(stint["driver_number"])

        # Encontrar telemetria base para o piloto e sessão
        base_tel = df_features_base[
            (df_features_base["session_key"] == skey)
            & (df_features_base["driver_number"] == dnum)
        ]

        if base_tel.empty:
            continue

        base_row = base_tel.iloc[0]

        # Stint range de voltas
        lap_start = int(stint["lap_start"])
        lap_end = (
            int(stint["lap_end"])
            if not pd.isna(stint["lap_end"])
            else int(lap_start + 10)
        )

        # Forçar limite realista se o número de voltas for muito alto ou inconsistente
        if lap_end < lap_start:
            lap_end = lap_start + 5

        num_laps = lap_end - lap_start + 1

        # Tempo base da pista
        pista_base = gp_base_times.get(skey, 85.0)

        # Diferenças de velocidade do piloto afetam o tempo de volta
        # Piloto com maior velocidade máxima tende a ser ligeiramente mais rápido
        speed_factor = (330.0 - base_row["max_speed"]) * 0.05

        for lap_idx in range(num_laps):
            lap_num = lap_start + lap_idx
            tyre_age = int(stint["tyre_age_at_start"]) + lap_idx

            # Penalidade de composto: SOFT é mais rápido que MEDIUM (+0.8s), que é mais rápido que HARD (+1.8s)
            comp_penalty = 0.0
            if stint["compound"] == "MEDIUM":
                comp_penalty = 0.8
            elif stint["compound"] == "HARD":
                comp_penalty = 1.8
            elif stint["compound"] in ["INTERMEDIATE", "WET"]:
                comp_penalty = 5.0

            # Efeito do desgaste do pneu (+0.12 segundos por volta de idade)
            wear_penalty = tyre_age * 0.12

            # Adicionar pequenas flutuações nas features por volta
            lap_max_speed = base_row["max_speed"] + np.random.normal(0, 3.0)
            lap_max_rpm = base_row["max_rpm"] + np.random.normal(0, 100.0)
            lap_throttle = max(
                0.0,
                min(
                    100.0, base_row["throttle_intensity_pct"] + np.random.normal(0, 2.0)
                ),
            )
            lap_brake = max(
                0.0,
                min(100.0, base_row["brake_intensity_pct"] + np.random.normal(0, 1.0)),
            )

            # Cálculo final do tempo da volta real simulado
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
        merged = pd.DataFrame(expanded_rows)
        output_file = os.path.join(DATA_DIR, "gold", "features_lap_data.parquet")
        merged.to_parquet(output_file, index=False)
        context.log.info(
            f"Criadas {len(merged)} linhas de features para a IA em {output_file}"
        )
    else:
        context.log.warn("Nenhuma linha de feature expandida gerada.")


@asset(group_name="Camada_Gold", deps=[gold_feature_engineering_lap_data])
def gold_lap_time_prediction_model(context: AssetExecutionContext) -> None:
    """
    Treina o modelo regressor RandomForest local para predição física de tempos de volta e desgaste.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    src_file = os.path.join(DATA_DIR, "gold", "features_lap_data.parquet")
    if not os.path.exists(src_file):
        return

    df = pd.read_parquet(src_file)
    if len(df) < 5:
        context.log.warn("Volume insuficiente para treinar o regressor de IA.")
        return

    # Features e Target
    features = [
        "throttle_intensity_pct",
        "brake_intensity_pct",
        "tyre_age_at_start",
        "compound_num",
        "max_speed",
    ]
    X = df[features]
    y = df["lap_duration_seconds"]

    # Treinamento do regressor Random Forest local (IA leve e robusta)
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)

    # Serialização no disco (MLOps standard)
    model_path = os.path.join(MODELS_DIR, "lap_regressor.joblib")
    joblib.dump(model, model_path)
    context.log.info(f"Modelo regressor treinado e salvo com sucesso em {model_path}")


@asset(
    group_name="Camada_Gold",
    deps=[gold_lap_time_prediction_model, gold_feature_engineering_lap_data],
)
def gold_lap_predictions(context: AssetExecutionContext) -> None:
    """
    Aplica o modelo serializado de IA preditiva para gerar tempos ideais e salvas na Gold.
    """
    model_path = os.path.join(MODELS_DIR, "lap_regressor.joblib")
    src_file = os.path.join(DATA_DIR, "gold", "features_lap_data.parquet")

    if not os.path.exists(model_path) or not os.path.exists(src_file):
        return

    model = joblib.load(model_path)
    df = pd.read_parquet(src_file)

    features = [
        "throttle_intensity_pct",
        "brake_intensity_pct",
        "tyre_age_at_start",
        "compound_num",
        "max_speed",
    ]
    X = df[features]

    # Gerando predições analíticas da IA
    df["predicted_lap_duration_seconds"] = model.predict(X)

    # Delta de performance (diferença entre o tempo real e o ideal físico estimado pela IA)
    df["delta_performance_seconds"] = (
        df["lap_duration_seconds"] - df["predicted_lap_duration_seconds"]
    )

    output_file = os.path.join(DATA_DIR, "gold", "lap_predictions.parquet")
    df.to_parquet(output_file, index=False)
    context.log.info(f"Predições de IA salvas na camada Gold em {output_file}")
