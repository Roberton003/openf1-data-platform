import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from src.web.database import get_db, run_query_async

router = APIRouter(prefix="/api")


def fetch_telemetry_from_db(
    conn: duckdb.DuckDBPyConnection, session_key: int, driver_number: int
) -> list[dict]:
    """
    Blocking DuckDB query to retrieve telemetry for a driver.
    """
    try:
        # Convert timestamp to ISO string format for clean JSON serialization
        query = """
            SELECT 
                strftime(date, '%Y-%m-%dT%H:%M:%S.%f') as date, 
                speed, 
                rpm, 
                n_gear, 
                throttle, 
                brake, 
                drs
            FROM fact_car_telemetry
            WHERE session_key = ? AND driver_number = ?
            ORDER BY date ASC
            LIMIT 1000
        """
        results = conn.execute(query, (session_key, driver_number)).fetchall()
        return [
            {
                "date": r[0],
                "speed": r[1],
                "rpm": r[2],
                "n_gear": r[3],
                "throttle": r[4],
                "brake": r[5],
                "drs": r[6],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar telemetria no DuckDB: {str(e)}"
        )


@router.get("/telemetry")
async def get_telemetry(
    session_key: int = Query(..., description="Chave da sessão da corrida"),
    driver_number: int = Query(..., description="Número do piloto"),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns high-frequency telemetry data for the selected driver and session.
    Delegates database execution to a worker thread.
    """
    return await run_query_async(
        fetch_telemetry_from_db, db, session_key, driver_number
    )
