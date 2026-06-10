import duckdb
from fastapi import APIRouter, Depends, HTTPException

from src.web.database import get_db, run_query_async

router = APIRouter(prefix="/api")


def fetch_pipeline_executions_from_db(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    try:
        query = """
            SELECT 
                strftime(execution_timestamp, '%Y-%m-%d %H:%M:%S') as execution_timestamp,
                run_id,
                pipeline_name,
                duration_seconds,
                rows_bronze,
                rows_silver,
                rows_quarantine,
                status
            FROM fact_pipeline_execution
            ORDER BY execution_timestamp DESC
        """
        results = conn.execute(query).fetchall()
        return [
            {
                "execution_timestamp": r[0],
                "run_id": r[1],
                "pipeline_name": r[2],
                "duration_seconds": r[3],
                "rows_bronze": r[4],
                "rows_silver": r[5],
                "rows_quarantine": r[6],
                "status": r[7],
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar execuções do pipeline: {str(e)}"
        )


@router.get("/pipeline_execution")
async def get_pipeline_execution(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """
    Returns pipeline lineage metadata metrics to feed the observability interface.
    """
    return await run_query_async(fetch_pipeline_executions_from_db, db)
