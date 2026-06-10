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
