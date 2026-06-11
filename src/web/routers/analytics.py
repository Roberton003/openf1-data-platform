import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

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
                strftime(rc.date, '%Y-%m-%dT%H:%M:%S.%f') as date
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
        # 1. Achar o primeiro timestamp onde o carro está na pista (speed > 100)
        t_query = """
            SELECT min(date) 
            FROM fact_car_telemetry 
            WHERE session_key = ? AND driver_number = ? AND speed > 100
        """
        t_res = conn.execute(t_query, (session_key, driver_number)).fetchone()
        if not t_res or not t_res[0]:
            return []
        start_date = t_res[0]

        # 2. Extrair coordenadas consecutivas para desenhar uma volta representativa
        query = """
            SELECT 
                l.x, 
                l.y, 
                t.speed,
                t.n_gear,
                t.throttle,
                t.brake
            FROM fact_car_location l
            ASOF JOIN fact_car_telemetry t 
                ON l.session_key = t.session_key 
               AND l.driver_number = t.driver_number 
               AND l.date >= t.date
            WHERE l.session_key = ? 
              AND l.driver_number = ? 
              AND l.date >= ?
            ORDER BY l.date ASC
            LIMIT 400
        """
        results = conn.execute(
            query, (session_key, driver_number, start_date)
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
