import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.web.database import get_db, run_query_async

router = APIRouter(prefix="/api")


def fetch_sessions_from_db(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    try:
        query = """
            SELECT 
                session_key, 
                year, 
                session_name, 
                session_type, 
                circuit_short_name, 
                country_name
            FROM dim_sessions
            ORDER BY year DESC, country_name ASC
        """
        results = conn.execute(query).fetchall()
        return [
            {
                "session_key": r[0],
                "year": r[1],
                "session_name": r[2],
                "session_type": r[3],
                "circuit_short_name": r[4],
                "country_name": r[5],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar sessões: {str(e)}")


def fetch_drivers_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        # Get active drivers who have stint data in this session
        query = """
            SELECT DISTINCT 
                d.driver_number, 
                d.full_name, 
                d.team_name, 
                d.name_acronym,
                d.country_code
            FROM dim_drivers d
            JOIN dim_stints s ON d.driver_number = s.driver_number
            WHERE s.session_key = ?
            ORDER BY d.team_name, d.driver_number
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "driver_number": r[0],
                "full_name": r[1],
                "team_name": r[2],
                "name_acronym": r[3],
                "country_code": r[4],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar pilotos da sessão: {str(e)}"
        )


def fetch_intervals_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        query = """
            SELECT 
                d.name_acronym as driver,
                d.team_name as team,
                i.gap_to_leader,
                i.interval,
                strftime(i.date, '%Y-%m-%dT%H:%M:%S.%f') as date
            FROM fact_intervals i
            JOIN dim_drivers d ON i.driver_number = d.driver_number
            WHERE i.session_key = ?
            ORDER BY i.date ASC
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "driver": r[0],
                "team": r[1],
                "gap_to_leader": r[2],
                "interval": r[3],
                "date": r[4],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar intervalos: {str(e)}"
        )


def fetch_pit_stops_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        query = """
            SELECT 
                d.name_acronym as driver,
                d.team_name as team,
                p.lap_number,
                p.stop_duration,
                p.lane_duration,
                p.pit_duration,
                strftime(p.date, '%Y-%m-%dT%H:%M:%S.%f') as date
            FROM fact_pit_stops p
            JOIN dim_drivers d ON p.driver_number = d.driver_number
            WHERE p.session_key = ?
            ORDER BY p.lap_number ASC, p.pit_duration DESC
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "driver": r[0],
                "team": r[1],
                "lap_number": r[2],
                "stop_duration": r[3],
                "lane_duration": r[4],
                "pit_duration": r[5],
                "date": r[6],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar pit stops: {str(e)}"
        )


@router.get("/sessions")
async def get_sessions(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """
    Returns lists of F1 Grand Prix sessions available in the DuckDB Silver database.
    """
    return await run_query_async(fetch_sessions_from_db, db)


@router.get("/drivers")
async def get_drivers(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns active drivers in the selected session.
    """
    return await run_query_async(fetch_drivers_from_db, db, session_key)


@router.get("/intervals")
async def get_intervals(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns chronological race gap intervals to study strategy.
    """
    return await run_query_async(fetch_intervals_from_db, db, session_key)


@router.get("/pit_stops")
async def get_pit_stops(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns pit stop information including durations for box strategy comparison.
    """
    return await run_query_async(fetch_pit_stops_from_db, db, session_key)


def fetch_weather_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        query = """
            SELECT 
                strftime(date, '%Y-%m-%dT%H:%M:%S.%f') as date,
                air_temperature,
                track_temperature,
                humidity,
                wind_speed,
                rainfall
            FROM dim_weather
            WHERE session_key = ?
            ORDER BY date ASC
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "date": r[0],
                "air_temperature": r[1],
                "track_temperature": r[2],
                "humidity": r[3],
                "wind_speed": r[4],
                "rainfall": r[5],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar clima no DuckDB: {str(e)}"
        )


@router.get("/weather")
async def get_weather(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns chronological weather conditions (temperatures, humidity, rainfall) for the session.
    """
    return await run_query_async(fetch_weather_from_db, db, session_key)


def fetch_stints_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        query = """
            SELECT 
                d.name_acronym as driver,
                d.team_name as team,
                s.stint_number,
                s.compound,
                s.lap_start,
                s.lap_end,
                s.tyre_age_at_start
            FROM dim_stints s
            JOIN dim_drivers d ON s.driver_number = d.driver_number
            WHERE s.session_key = ?
            ORDER BY d.name_acronym, s.stint_number ASC
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "driver": r[0],
                "team": r[1],
                "stint_number": r[2],
                "compound": r[3],
                "lap_start": r[4],
                "lap_end": r[5],
                "tyre_age_at_start": r[6],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar stints no DuckDB: {str(e)}"
        )


@router.get("/stints")
async def get_stints(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns historical tyre stints per driver in the selected session.
    """
    return await run_query_async(fetch_stints_from_db, db, session_key)


def fetch_race_control_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        query = """
            SELECT 
                d.name_acronym as driver,
                rc.category,
                rc.flag,
                rc.message,
                strftime(rc.date::TIMESTAMP, '%Y-%m-%dT%H:%M:%S.%f') as date
            FROM fact_race_control rc
            LEFT JOIN dim_drivers d ON rc.driver_number = d.driver_number
            WHERE rc.session_key = ?
            ORDER BY rc.date ASC
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "driver": r[0],
                "category": r[1],
                "flag": r[2],
                "message": r[3],
                "date": r[4],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar controle de prova: {str(e)}"
        )


@router.get("/race_control")
async def get_race_control(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns chronological FIA race control event messages.
    """
    return await run_query_async(fetch_race_control_from_db, db, session_key)


def fetch_winner_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        query = """
            SELECT 
                d.name_acronym as driver,
                d.full_name,
                d.team_name as team,
                r.position,
                r.points,
                r.number_of_laps
            FROM fact_session_results r
            JOIN dim_drivers d ON r.driver_number = d.driver_number
            WHERE r.session_key = ? AND r.position = 1
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "driver": r[0],
                "full_name": r[1],
                "team": r[2],
                "position": r[3],
                "points": r[4],
                "number_of_laps": r[5],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar vencedor no DuckDB: {str(e)}"
        )


@router.get("/winner")
async def get_winner(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns the winner of the selected Grand Prix session.
    """
    return await run_query_async(fetch_winner_from_db, db, session_key)


def fetch_duel_location_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int, driver_number: int
) -> list[dict]:
    try:
        # 1. Achar o primeiro timestamp unificado da sessão (speed > 100 para qualquer piloto)
        t_query = """
            SELECT min(date) 
            FROM fact_car_telemetry 
            WHERE session_key = ? AND speed > 100
        """
        t_res = conn.execute(t_query, (session_key,)).fetchone()
        if not t_res or not t_res[0]:
            return []
        start_date = t_res[0]

        # 2. Obter a contagem total de registros do piloto para calcular a amostragem
        count_query = """
            SELECT COUNT(*) 
            FROM fact_car_location 
            WHERE session_key = ? AND driver_number = ? AND date >= ?
        """
        count_res = conn.execute(
            count_query, (session_key, driver_number, start_date)
        ).fetchone()
        total_records = count_res[0] if count_res else 0
        if total_records == 0:
            return []

        # Determinar o tamanho do passo (step) para obter cerca de 1500 pontos de amostragem
        target_points = 1500
        step = max(1, total_records // target_points)

        # 3. Extrair coordenadas com ASOF JOIN e amostragem sistemática
        query = """
            WITH numbered_locations AS (
                SELECT 
                    l.x, 
                    l.y, 
                    t.speed,
                    t.n_gear,
                    t.throttle,
                    t.brake,
                    ROW_NUMBER() OVER(ORDER BY l.date ASC) as rn
                FROM fact_car_location l
                ASOF JOIN fact_car_telemetry t 
                    ON l.session_key = t.session_key 
                   AND l.driver_number = t.driver_number 
                   AND l.date >= t.date
                WHERE l.session_key = ? 
                  AND l.driver_number = ? 
                  AND l.date >= ?
            )
            SELECT x, y, speed, n_gear, throttle, brake 
            FROM numbered_locations 
            WHERE rn % ? = 0
            ORDER BY rn ASC
        """
        results = conn.execute(
            query, (session_key, driver_number, start_date, step)
        ).fetchall()
        return [
            {
                "x": r[0],
                "y": r[1],
                "speed": r[2],
                "gear": r[3],
                "throttle": r[4],
                "brake": r[5],
            }
            for r in results
            if r[0] is not None and r[1] is not None
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar trajetórias do duelo: {str(e)}"
        )


@router.get("/duel/location")
async def get_duel_location(
    session_key: int = Query(..., description="Chave da sessão"),
    driver_number: int = Query(..., description="Número do piloto"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Retorna a trajetória 2D consecutiva (volta representativa) e telemetria do piloto para o Speed Track Map.
    """
    return await run_query_async(
        fetch_duel_location_from_db, db, session_key, driver_number
    )


def fetch_duel_metrics_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int, driver_1: int, driver_2: int
) -> dict:
    try:
        # Obter métricas de telemetria agregadas
        query = """
            SELECT 
                driver_number,
                MAX(speed) as max_speed,
                MAX(rpm) as max_rpm,
                AVG(CASE WHEN throttle > 90 THEN 1.0 ELSE 0.0 END) * 100 as full_throttle_pct,
                AVG(CASE WHEN brake > 50 THEN 1.0 ELSE 0.0 END) * 100 as heavy_brake_pct,
                AVG(CASE WHEN drs > 0 THEN 1.0 ELSE 0.0 END) * 100 as drs_pct
            FROM fact_car_telemetry
            WHERE session_key = ? AND driver_number IN (?, ?)
            GROUP BY driver_number
        """
        results = conn.execute(query, (session_key, driver_1, driver_2)).fetchall()

        # Puxar tempos de melhor pitstop de cada piloto
        pit_query = """
            SELECT driver_number, MIN(pit_duration) as best_pit
            FROM fact_pit_stops
            WHERE session_key = ? AND driver_number IN (?, ?)
            GROUP BY driver_number
        """
        pit_results = conn.execute(
            pit_query, (session_key, driver_1, driver_2)
        ).fetchall()
        pits = {r[0]: r[1] for r in pit_results}

        metrics = {}
        for r in results:
            drv_num = r[0]
            metrics[str(drv_num)] = {
                "max_speed": r[1] or 0,
                "max_rpm": r[2] or 0,
                "full_throttle_pct": round(r[3] or 0.0, 1),
                "heavy_brake_pct": round(r[4] or 0.0, 1),
                "drs_pct": round(r[5] or 0.0, 1),
                "best_pit": pits.get(drv_num, "-"),
            }
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao calcular métricas do duelo: {str(e)}"
        )


@router.get("/duel/metrics")
async def get_duel_metrics(
    session_key: int = Query(..., description="Chave da sessão"),
    driver_1: int = Query(..., description="Número do primeiro piloto"),
    driver_2: int = Query(..., description="Número do segundo piloto"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Retorna métricas comparativas agregadas para o duelo de dois pilotos.
    """
    return await run_query_async(
        fetch_duel_metrics_from_db, db, session_key, driver_1, driver_2
    )


def fetch_lap_predictions_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int, driver_number: int
) -> list[dict]:
    try:
        # Consulta as predições de IA gravadas na camada Gold
        query = """
            SELECT 
                stint_number,
                compound,
                tyre_age_at_start,
                lap_duration_seconds,
                predicted_lap_duration_seconds,
                delta_performance_seconds
            FROM gold_lap_predictions
            WHERE session_key = ? AND driver_number = ?
            ORDER BY stint_number ASC
        """
        results = conn.execute(query, (session_key, driver_number)).fetchall()
        return [
            {
                "stint_number": r[0],
                "compound": r[1],
                "tyre_age": r[2],
                "actual_lap_time": round(r[3], 3) if r[3] is not None else None,
                "predicted_lap_time": round(r[4], 3) if r[4] is not None else None,
                "delta": round(r[5], 3) if r[5] is not None else None,
            }
            for r in results
        ]
    except Exception:
        # Retorna lista vazia caso a tabela Gold ainda não exista ou esteja vazia
        return []


@router.get("/predictions/lap_time")
async def get_lap_predictions(
    session_key: int = Query(..., description="Chave da sessão"),
    driver_number: int = Query(..., description="Número do piloto"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Retorna os tempos de volta reais vs preditos pela IA na camada Gold para a sessão.
    """
    return await run_query_async(
        fetch_lap_predictions_from_db, db, session_key, driver_number
    )


def fetch_overtakes_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> list[dict]:
    try:
        # Join com dim_drivers para obter os acrônimos dos pilotos
        query = """
            SELECT 
                d1.name_acronym as overtaking_driver,
                d2.name_acronym as overtaken_driver,
                o.position,
                strftime(o.date::TIMESTAMP, '%Y-%m-%dT%H:%M:%S.%f') as date
            FROM fact_overtakes o
            LEFT JOIN dim_drivers d1 ON o.overtaking_driver_number = d1.driver_number
            LEFT JOIN dim_drivers d2 ON o.overtaken_driver_number = d2.driver_number
            WHERE o.session_key = ?
            ORDER BY o.date ASC
        """
        results = conn.execute(query, (session_key,)).fetchall()
        return [
            {
                "overtaking_driver": (
                    r[0] if r[0] else str(r[4] if len(r) > 4 else "")
                ),  # Fallback se não encontrar piloto
                "overtaken_driver": r[1] if r[1] else str(r[5] if len(r) > 5 else ""),
                "position": r[2],
                "date": r[3],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar ultrapassagens no DuckDB: {str(e)}"
        )


@router.get("/overtakes")
async def get_overtakes(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Retorna a lista de ultrapassagens cronológicas da sessão.
    """
    return await run_query_async(fetch_overtakes_from_db, db, session_key)


def fetch_pipeline_executions_from_db(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    try:
        query = """
            SELECT 
                run_id,
                pipeline_name,
                session_key,
                execution_timestamp,
                duration_seconds,
                status,
                total_rows_processed
            FROM fact_pipeline_execution
            ORDER BY execution_timestamp DESC
        """
        results = conn.execute(query).fetchall()
        return [
            {
                "run_id": r[0],
                "pipeline_name": r[1],
                "session_key": r[2],
                "execution_timestamp": r[3],
                "duration_seconds": round(r[4], 2) if r[4] is not None else None,
                "status": r[5],
                "total_rows_processed": r[6],
            }
            for r in results
        ]
    except Exception:
        return []


@router.get("/pipeline_execution")
async def get_pipeline_executions(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """
    Retorna o histórico de observabilidade de freshness do processamento dos pipelines.
    """
    return await run_query_async(fetch_pipeline_executions_from_db, db)


class SQLQueryRequest(BaseModel):
    query: str


def execute_safe_sql_query(
    conn: duckdb.DuckDBPyConnection, raw_query: str
) -> list[dict]:
    # 🛡️ Validação defensiva de segurança analítica (limita a SELECT/WITH e previne DDL/DML)
    forbidden_tokens = [
        "drop",
        "delete",
        "insert",
        "update",
        "create",
        "alter",
        "vacuum",
        "truncate",
        "system",
        "write_parquet",
        "copy",
    ]
    query_lower = raw_query.lower()
    if any(token in query_lower for token in forbidden_tokens):
        raise HTTPException(
            status_code=400,
            detail="Operação não autorizada. Apenas consultas de leitura (SELECT, WITH) são permitidas.",
        )

    try:
        # Executa a query e retorna como DataFrame do Pandas, convertendo em registros JSON
        # O DuckDB lida nativamente com o retorno em Pandas DataFrame via view Parquet
        df = conn.execute(raw_query).df()
        # Tratamento de nulos/NaNs típicos de bancos analíticos para serialização JSON limpa
        df = df.where(df.notnull(), None)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro de sintaxe SQL ou execução no DuckDB: {str(e)}",
        )


@router.post("/analytics/query")
async def execute_adhoc_query(
    request: SQLQueryRequest, db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Data Gateway de Analytics para execução segura de queries SQL (SELECT/WITH)
    diretamente no Lakehouse mapeado via DuckDB.
    """
    return await run_query_async(execute_safe_sql_query, db, request.query)


class ChatRequest(BaseModel):
    session_key: int
    question: str


def execute_hybrid_semantic_search(
    conn: duckdb.DuckDBPyConnection, session_key: int, question: str
) -> dict:
    import numpy as np

    # 1. Busca mensagens qualitativas de pista reais registradas na Silver
    query_messages = """
        SELECT 
            strftime(date::TIMESTAMP, '%Y-%m-%dT%H:%M:%S.%f') as date_str,
            driver_number,
            category,
            flag,
            message,
            date
        FROM fact_race_control
        WHERE session_key = ? AND message IS NOT NULL
        ORDER BY date ASC
    """
    rows = conn.execute(query_messages, (session_key,)).fetchall()

    if not rows:
        return {
            "answer": (
                "### 🏎️ OpenF1 Insight Híbrido (Modo Local)\n\n"
                "Nenhuma mensagem de rádio ou controle de prova foi encontrada para esta sessão no Lakehouse.\n\n"
                "> [!NOTE]\n"
                "Certifique-se de que os dados de Race Control foram devidamente ingeridos na camada Silver."
            ),
            "relevance": 0.0,
            "data": [],
        }

    documents = [r[4] for r in rows]

    # 2. Computa similaridade local via TF-IDF (Sentence Similarity esparsa)
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
        query_vector = vectorizer.transform([question])
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
    except Exception:
        best_idx = 0
        best_score = 0.0

    # Se a similaridade for muito baixa, avisa o usuário de forma amigável
    if best_score < 0.02:
        return {
            "answer": (
                f"### 🏎️ OpenF1 Insight Híbrido (Modo Local)\n\n"
                f'Nenhum alerta de pista ou rádio relevante foi encontrado para a pergunta: *"{question}"*.\n\n'
                f"*   **Melhor correspondência (Relevância: {best_score:.2%}):**\n"
                f'    > "{rows[best_idx][4]}"\n\n'
                f"> [!TIP]\n"
                f"Tente usar termos chaves de prova como 'flag', 'green', 'pit', 'engine', 'safety car' ou 'driver'."
            ),
            "relevance": best_score,
            "data": [],
        }

    matched_row = rows[best_idx]
    date_str, driver_number, category, flag, message, event_date = matched_row

    # Resolvendo o nome do piloto se disponível
    driver_name = "N/A"
    if driver_number:
        driver_row = conn.execute(
            "SELECT full_name, team_name FROM dim_drivers WHERE driver_number = ?",
            (driver_number,),
        ).fetchone()
        if driver_row:
            driver_name = f"{driver_row[0]} ({driver_row[1]})"

    # 3. Busca telemetria física associada nos 15s seguintes à data do evento no DuckDB
    telemetry_data = None
    telemetry_summary = ""

    try:
        # Checa se a tabela fact_car_telemetry existe e tem registros
        check_telemetry = conn.execute(
            "SELECT count(*) FROM fact_car_telemetry WHERE session_key = ?",
            (session_key,),
        ).fetchone()
        if check_telemetry and check_telemetry[0] > 0:
            if driver_number:
                # Telemetria do piloto específico
                query_telemetry = """
                    SELECT 
                        AVG(speed) as avg_speed,
                        MAX(rpm) as max_rpm,
                        MIN(n_gear) as min_gear
                    FROM fact_car_telemetry
                    WHERE session_key = ? 
                      AND driver_number = ?
                      AND date >= ?::TIMESTAMP
                      AND date <= ?::TIMESTAMP + INTERVAL '15 seconds'
                """
                t_row = conn.execute(
                    query_telemetry,
                    (session_key, driver_number, event_date, event_date),
                ).fetchone()
                if t_row and t_row[0] is not None:
                    telemetry_data = {
                        "avg_speed": round(t_row[0], 1),
                        "max_rpm": int(t_row[1]) if t_row[1] is not None else None,
                        "min_gear": int(t_row[2]) if t_row[2] is not None else None,
                    }
                    telemetry_summary = (
                        f"\n**Telemetria do Piloto nos 15s seguintes ao Alerta:**\n"
                        f"*   **Velocidade Média:** {telemetry_data['avg_speed']} km/h\n"
                        f"*   **RPM Máximo:** {telemetry_data['max_rpm']}\n"
                        f"*   **Marcha Mínima Utilizada:** {telemetry_data['min_gear']}\n"
                    )
            else:
                # Telemetria média de todos os pilotos na pista (Bandeira amarela geral/Safety Car)
                query_telemetry_global = """
                    SELECT 
                        AVG(speed) as avg_speed,
                        MIN(speed) as min_speed
                    FROM fact_car_telemetry
                    WHERE session_key = ?
                      AND date >= ?::TIMESTAMP
                      AND date <= ?::TIMESTAMP + INTERVAL '15 seconds'
                """
                tg_row = conn.execute(
                    query_telemetry_global, (session_key, event_date, event_date)
                ).fetchone()
                if tg_row and tg_row[0] is not None:
                    telemetry_data = {
                        "avg_speed": round(tg_row[0], 1),
                        "min_speed": (
                            round(tg_row[1], 1) if tg_row[1] is not None else None
                        ),
                    }
                    telemetry_summary = (
                        f"\n**Impacto de Velocidade Média na Pista (Global nos 15s seguintes):**\n"
                        f"*   **Velocidade Média Geral:** {telemetry_data['avg_speed']} km/h\n"
                        f"*   **Velocidade Mínima Registrada:** {telemetry_data['min_speed']} km/h (indica desaceleração sob bandeira)\n"
                    )
    except Exception:
        # Se a tabela de telemetria estiver vazia ou indisponível
        telemetry_summary = (
            f"\n*(Telemetria física indisponível no DuckDB para o instante do evento)*"
        )

    # 4. Formata a resposta analítica híbrida rica em Markdown
    markdown_answer = (
        f"### 🏎️ OpenF1 Insight Híbrido (Modo Local TF-IDF)\n\n"
        f'**Pergunta Analítica:** *"{question}"*\n\n'
        f"**Mensagem de Pista Encontrada:**\n"
        f'> "{message}"\n\n'
        f"*   **Instante:** {date_str}\n"
        f"*   **Categoria:** {category} | **Bandeira:** {flag if flag else 'N/A'}\n"
        f"*   **Piloto Associado:** {driver_name if driver_number else 'Geral (Todos na Pista)'}\n"
        f"*   **Relevância da Busca:** {best_score:.2%}\n"
        f"{telemetry_summary}\n"
        f"---\n"
        f"> [!NOTE]\n"
        f"Resposta gerada localmente de forma serverless (Scikit-Learn TF-IDF + DuckDB SQL), "
        f"garantindo 100% de precisão matemática e zero custos de API de nuvem."
    )

    return {
        "answer": markdown_answer,
        "relevance": best_score,
        "data": {
            "message": message,
            "date": date_str,
            "category": category,
            "flag": flag,
            "driver_number": driver_number,
            "driver_name": driver_name,
            "telemetry": telemetry_data,
        },
    }


@router.post("/analytics/chat")
async def execute_chat_query(
    request: ChatRequest, db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Endpoint conversacional analítico local RAG (TF-IDF + DuckDB SQL) de custo zero.
    """
    return await run_query_async(
        execute_hybrid_semantic_search, db, request.session_key, request.question
    )
