import argparse
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://api.openf1.org/v1"
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")

# Grid de pilotos foco para análises comparativas (Temporada 2025)
PILOTOS_FOCO = {
    1: "Max Verstappen",
    16: "Charles Leclerc",
    44: "Lewis Hamilton",
    4: "Lando Norris",
    81: "Oscar Piastri",
}

# Semáforo para controlar concorrência de rede simultânea na API OpenF1 (DEC-008, §1)
# Evita bloqueios por rate limiting (HTTP 429) e timeouts de rede na telemetria
api_semaphore = threading.Semaphore(2)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_endpoint(endpoint: str, params: dict = None) -> list:
    """
    Consome um endpoint da API OpenF1 com retry resilience e tratamento HTTP 404/429.
    """
    url = f"{BASE_URL}/{endpoint}"
    with api_semaphore:
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Trata erro 404 (sem dados) silenciosamente para não interromper o fluxo
            if e.response.status_code == 404:
                return []
            raise e
        except requests.exceptions.RequestException as e:
            # Qualquer outra falha de rede dispara retry via Tenacity
            raise e


def get_session_info(year: int, gp_name: Optional[str], session_name: str) -> dict:
    """
    Pesquisa a sessão correspondente ao ano, gp e tipo na API.
    Executa fallback automático para 2024 se não encontrar registros de 2025.
    """
    sessions = fetch_endpoint("sessions", {"year": year})

    if not sessions and year == 2025:
        print(
            f"Nenhum dado encontrado para a temporada de 2025. Executando fallback para 2024..."
        )
        year = 2024
        sessions = fetch_endpoint("sessions", {"year": year})

    if not sessions:
        raise ValueError(f"Nenhuma sessão encontrada para a temporada {year}.")

    df = pd.DataFrame(sessions)

    # Filtrar por GP se fornecido
    if gp_name:
        gp_mask = df["country_name"].str.contains(gp_name, case=False, na=False) | df[
            "circuit_short_name"
        ].str.contains(gp_name, case=False, na=False)
        df_gp = df[gp_mask]
        if df_gp.empty:
            print(
                f"GP '{gp_name}' não mapeado na API. Usando GP mais recente disponível."
            )
        else:
            df = df_gp

    # Filtrar por tipo de sessão
    session_mask = df["session_name"].str.contains(session_name, case=False, na=False)
    df_session = df[session_mask]

    if df_session.empty:
        # Se não achar a sessão específica, pega a última ordenada por data
        print(
            f"Sessão '{session_name}' não encontrada. Selecionando a mais recente do GP/Temporada."
        )
        df = df.sort_values("date_start", ascending=False)
        latest_session = df.iloc[0].to_dict()
    else:
        latest_session = (
            df_session.sort_values("date_start", ascending=False).iloc[0].to_dict()
        )

    latest_session["year_actual"] = year
    return latest_session


def extract_driver_telemetry(
    session_key: int, driver_number: int, driver_name: str
) -> tuple:
    """
    Worker para extração paralela de telemetria física (car_data) e intervalos por piloto.
    """
    print(f" -> [{driver_name} - #{driver_number}] Iniciando extração de telemetria...")

    # 1. Extração de car_data (telemetria 3.7Hz)
    telemetry = fetch_endpoint(
        "car_data",
        {
            "session_key": session_key,
            "driver_number": driver_number,
            "limit": 30000,  # Limite realista de amostragem por piloto para testes de pipeline
        },
    )

    # 2. Extração de intervalos (intervals)
    intervals = fetch_endpoint(
        "intervals", {"session_key": session_key, "driver_number": driver_number}
    )

    print(
        f" -> [{driver_name} - #{driver_number}] Concluído. Tel: {len(telemetry)} linhas | Gaps: {len(intervals)} linhas"
    )
    return (driver_number, telemetry, intervals)


def run_extraction(year: int, gp_name: Optional[str], session_name: str):
    """
    Pipeline de Ingestão da Camada Bronze.
    """
    print(f"=== 🏎️ OpenF1 Data Ingestion: Bronze Layer ===")
    print(f"Temporada: {year} | GP: {gp_name or 'Último'} | Sessão: {session_name}")

    # 1. Resolução da Sessão
    session_info = get_session_info(year, gp_name, session_name)
    session_key = int(session_info["session_key"])
    actual_year = session_info["year_actual"]
    gp_resolved = session_info["country_name"].replace(" ", "_")
    session_resolved = session_info["session_name"].replace(" ", "_")

    print(
        f"Sessão Resolvida: {session_info['session_name']} - Key: {session_key} (Ano: {actual_year})"
    )

    # 2. Definir caminho de salvamento baseado em partições Lakehouse (Bronze)
    partition_path = os.path.join(
        DATA_DIR,
        "bronze",
        f"year={actual_year}",
        f"gp={gp_resolved}",
        f"session={session_resolved}",
    )
    os.makedirs(partition_path, exist_ok=True)

    # 3. Extrair metadados gerais da corrida (Lote único da Sessão)
    metadata_endpoints = {
        "weather": "weather",
        "pit_stops": "pit",
        "stints": "stints",
        "race_control": "race_control",
        "session_result": "session_result",
        "drivers": "drivers",
    }

    for ep_filename, ep_route in metadata_endpoints.items():
        print(f"Extraindo metadado: {ep_filename}...")
        data = fetch_endpoint(ep_route, {"session_key": session_key})
        if data:
            df = pd.DataFrame(data)
            # Cast de colunas com tipos mistos (DEC-003) para prevenir problemas de inferência do PyArrow
            for col in ["gap_to_leader", "interval"]:
                if col in df.columns:
                    df[col] = df[col].astype(str)
            output_file = os.path.join(partition_path, f"{ep_filename}.parquet")
            df.to_parquet(output_file, index=False)
            print(f" -> Salvo {len(df)} linhas em {output_file}")
        else:
            print(f" -> Nenhum registro retornado para {ep_filename}")

    # Salvar metadado da própria sessão para dim_sessions
    df_sess = pd.DataFrame([session_info])
    df_sess.to_parquet(os.path.join(partition_path, "sessions.parquet"), index=False)

    # 4. Extração concorrente de telemetria dos pilotos selecionados
    all_telemetry = []
    all_intervals = []

    print(
        f"Iniciando extração de telemetria dos pilotos foco com ThreadPoolExecutor..."
    )

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for d_num, d_name in PILOTOS_FOCO.items():
            futures.append(
                executor.submit(extract_driver_telemetry, session_key, d_num, d_name)
            )

        for fut in as_completed(futures):
            try:
                d_num, tel, inter = fut.result()
                if tel:
                    all_telemetry.extend(tel)
                if inter:
                    all_intervals.extend(inter)
            except Exception as e:
                print(f"Erro na extração paralela do piloto: {e}")

    # 5. Salvar telemetria consolidada da sessão
    if all_telemetry:
        df_tel = pd.DataFrame(all_telemetry)
        # Forçar conversão e coerção de tipos básicos para evitar inconsistências no PyArrow
        df_tel["driver_number"] = df_tel["driver_number"].astype(int)
        df_tel["session_key"] = df_tel["session_key"].astype(int)

        output_tel = os.path.join(partition_path, "car_data.parquet")
        df_tel.to_parquet(output_tel, index=False)
        print(f"Consolidado car_data: {len(df_tel)} linhas salvas em {output_tel}")
    else:
        print(
            "Aviso: Nenhuma telemetria extraída para os pilotos focados nesta sessão."
        )

    # 6. Salvar intervalos consolidados da sessão
    if all_intervals:
        df_int = pd.DataFrame(all_intervals)
        df_int["driver_number"] = df_int["driver_number"].astype(int)
        df_int["session_key"] = df_int["session_key"].astype(int)

        # Cast de colunas com tipos mistos (DEC-003) para prevenir problemas de inferência do PyArrow
        for col in ["gap_to_leader", "interval"]:
            if col in df_int.columns:
                df_int[col] = df_int[col].astype(str)

        output_int = os.path.join(partition_path, "intervals.parquet")
        df_int.to_parquet(output_int, index=False)
        print(f"Consolidado intervals: {len(df_int)} linhas salvas em {output_int}")
    else:
        print("Aviso: Nenhum dado de intervalo extraído para esta sessão.")

    print(f"Ingestão da Bronze finalizada com sucesso em: {partition_path}\n")
    return partition_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline de Ingestão F1 - Camada Bronze"
    )
    parser.add_argument(
        "--year", type=int, default=2025, help="Ano da temporada F1 (padrão: 2025)"
    )
    parser.add_argument(
        "--gp", type=str, default=None, help="Nome do GP ou País da corrida"
    )
    parser.add_argument(
        "--session", type=str, default="Race", help="Nome da sessão (padrão: Race)"
    )

    args = parser.parse_args()

    run_extraction(args.year, args.gp, args.session)
