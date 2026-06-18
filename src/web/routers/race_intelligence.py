from __future__ import annotations

from typing import Any, Literal

import duckdb
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.web.database import get_db, run_query_async

router = APIRouter(prefix="/api/race_intelligence", tags=["race_intelligence"])

AvailabilityReason = Literal[
    "ok",
    "dataset_absent",
    "no_rows_for_session",
    "schema_incompatible",
    "gold_unavailable",
    "pipeline_history_unavailable",
]


class EmptyState(BaseModel):
    available: bool
    reason: AvailabilityReason
    message: str


class SessionInfo(BaseModel):
    session_key: int
    year: int | None = None
    session_name: str | None = None
    session_type: str | None = None
    circuit_short_name: str | None = None
    country_name: str | None = None


class WinnerInfo(BaseModel):
    driver_number: int | None = None
    driver: str | None = None
    full_name: str | None = None
    team: str | None = None
    position: int | None = None
    points: float | None = None
    number_of_laps: int | None = None


class SessionSummaryData(BaseModel):
    session: SessionInfo
    winner: WinnerInfo | None = None
    driver_count: int = 0
    event_count: int = 0
    pit_stop_count: int = 0
    stint_count: int = 0
    gold_predictions_available: bool = False
    latest_pipeline_status: str | None = None


class SessionSummaryResponse(BaseModel):
    available: bool
    reason: AvailabilityReason
    data: SessionSummaryData | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverOption(BaseModel):
    driver_number: int
    full_name: str | None = None
    name_acronym: str | None = None
    team_name: str | None = None
    country_code: str | None = None
    has_telemetry: bool = False
    has_predictions: bool = False


class DriverOptionsResponse(BaseModel):
    available: bool
    reason: AvailabilityReason
    data: list[DriverOption] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    event_type: Literal["race_control", "pit_stop", "overtake"]
    timestamp: str | None = None
    lap_number: int | None = None
    driver: str | None = None
    severity: Literal["info", "warning", "critical"] = "info"
    source: str
    label: str
    details: dict[str, Any] = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    available: bool
    reason: AvailabilityReason
    data: list[TimelineEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineExecution(BaseModel):
    run_id: str | None = None
    pipeline_name: str | None = None
    session_key: int | None = None
    execution_timestamp: str | None = None
    duration_seconds: float | None = None
    status: str | None = None
    total_rows_processed: int | None = None
    total_rows_bronze: int | None = None
    total_rows_silver: int | None = None
    total_rows_quarantine: int | None = None
    quarantine_rate: float | None = None


class PipelineHealthData(BaseModel):
    latest_execution: PipelineExecution | None = None
    history: list[PipelineExecution] = Field(default_factory=list)
    health_status: Literal["healthy", "warning", "unavailable"] = "unavailable"


class PipelineHealthResponse(BaseModel):
    available: bool
    reason: AvailabilityReason
    data: PipelineHealthData | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PredictionStatusData(BaseModel):
    available: bool
    session_key: int
    prediction_count: int = 0
    driver_count: int = 0
    min_delta: float | None = None
    max_delta: float | None = None
    avg_delta: float | None = None


class PredictionStatusResponse(BaseModel):
    available: bool
    reason: AvailabilityReason
    data: PredictionStatusData | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DuelDriverMetrics(BaseModel):
    driver_number: int
    max_speed: float | None = None
    max_rpm: float | None = None
    full_throttle_pct: float | None = None
    heavy_brake_pct: float | None = None
    drs_pct: float | None = None
    best_pit: float | None = None
    prediction_delta_avg: float | None = None


class DuelPoint(BaseModel):
    driver_number: int
    x: int | None = None
    y: int | None = None
    speed: float | None = None
    gear: int | None = None


class DriverDuelData(BaseModel):
    session_key: int
    drivers: dict[str, DuelDriverMetrics]
    sample_points: list[DuelPoint] = Field(default_factory=list)


class DriverDuelResponse(BaseModel):
    available: bool
    reason: AvailabilityReason
    data: DriverDuelData | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _session_exists(conn: duckdb.DuckDBPyConnection, session_key: int) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM dim_sessions WHERE session_key = ?", (session_key,)
    ).fetchone()
    return bool(row and row[0] > 0)


def _empty_response(reason: AvailabilityReason, message: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "data": None,
        "metadata": {
            "empty_state": EmptyState(
                available=False, reason=reason, message=message
            ).model_dump()
        },
    }


def _format_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _table_columns(conn: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {row[1] for row in rows}


def _column_or_null(columns: set[str], column_name: str, sql_type: str) -> str:
    if column_name in columns:
        return column_name
    return f"CAST(NULL AS {sql_type}) AS {column_name}"


def _severity_for_flag(flag: str | None) -> Literal["info", "warning", "critical"]:
    flag_norm = (flag or "").upper()
    if "RED" in flag_norm:
        return "critical"
    if "YELLOW" in flag_norm or "SAFETY" in flag_norm:
        return "warning"
    return "info"


def fetch_session_summary(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> dict[str, Any]:
    session_row = conn.execute(
        """
        SELECT session_key, year, session_name, session_type, circuit_short_name, country_name
        FROM dim_sessions
        WHERE session_key = ?
        """,
        (session_key,),
    ).fetchone()
    if not session_row:
        return _empty_response(
            "no_rows_for_session", "Sessão não encontrada no lakehouse."
        )

    winner_row = conn.execute(
        """
        SELECT r.driver_number, d.name_acronym, d.full_name, d.team_name, r.position, r.points, r.number_of_laps
        FROM fact_session_results r
        LEFT JOIN dim_drivers d ON r.driver_number = d.driver_number
        WHERE r.session_key = ? AND r.position = 1
        LIMIT 1
        """,
        (session_key,),
    ).fetchone()
    counts = conn.execute(
        """
        SELECT
            (SELECT COUNT(DISTINCT driver_number) FROM dim_stints WHERE session_key = ?) AS driver_count,
            (SELECT COUNT(*) FROM fact_race_control WHERE session_key = ?) AS race_control_count,
            (SELECT COUNT(*) FROM fact_pit_stops WHERE session_key = ?) AS pit_stop_count,
            (SELECT COUNT(*) FROM dim_stints WHERE session_key = ?) AS stint_count,
            (SELECT COUNT(*) FROM gold_lap_predictions WHERE session_key = ?) AS prediction_count
        """,
        (session_key, session_key, session_key, session_key, session_key),
    ).fetchone()
    latest_pipeline = conn.execute(
        """
        SELECT status
        FROM fact_pipeline_execution
        WHERE session_key = ?
        ORDER BY execution_timestamp DESC
        LIMIT 1
        """,
        (session_key,),
    ).fetchone()

    data = SessionSummaryData(
        session=SessionInfo(
            session_key=session_row[0],
            year=session_row[1],
            session_name=session_row[2],
            session_type=session_row[3],
            circuit_short_name=session_row[4],
            country_name=session_row[5],
        ),
        winner=(
            WinnerInfo(
                driver_number=winner_row[0],
                driver=winner_row[1],
                full_name=winner_row[2],
                team=winner_row[3],
                position=winner_row[4],
                points=winner_row[5],
                number_of_laps=winner_row[6],
            )
            if winner_row
            else None
        ),
        driver_count=counts[0] or 0,
        event_count=counts[1] or 0,
        pit_stop_count=counts[2] or 0,
        stint_count=counts[3] or 0,
        gold_predictions_available=bool(counts[4] and counts[4] > 0),
        latest_pipeline_status=latest_pipeline[0] if latest_pipeline else None,
    )
    return {
        "available": True,
        "reason": "ok",
        "data": data.model_dump(),
        "metadata": {},
    }


def fetch_driver_options(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> dict[str, Any]:
    if not _session_exists(conn, session_key):
        return {
            "available": False,
            "reason": "no_rows_for_session",
            "data": [],
            "metadata": {},
        }

    rows = conn.execute(
        """
        SELECT DISTINCT d.driver_number, d.full_name, d.name_acronym, d.team_name, d.country_code,
               EXISTS (
                   SELECT 1 FROM fact_car_telemetry t
                   WHERE t.session_key = ? AND t.driver_number = d.driver_number
               ) AS has_telemetry,
               EXISTS (
                   SELECT 1 FROM gold_lap_predictions p
                   WHERE p.session_key = ? AND p.driver_number = d.driver_number
               ) AS has_predictions
        FROM dim_drivers d
        JOIN dim_stints s ON d.driver_number = s.driver_number
        WHERE s.session_key = ?
        ORDER BY d.team_name, d.driver_number
        """,
        (session_key, session_key, session_key),
    ).fetchall()
    data = [
        DriverOption(
            driver_number=row[0],
            full_name=row[1],
            name_acronym=row[2],
            team_name=row[3],
            country_code=row[4],
            has_telemetry=bool(row[5]),
            has_predictions=bool(row[6]),
        ).model_dump()
        for row in rows
    ]
    return {
        "available": bool(data),
        "reason": "ok" if data else "no_rows_for_session",
        "data": data,
        "metadata": {"count": len(data)},
    }


def fetch_strategy_timeline(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> dict[str, Any]:
    if not _session_exists(conn, session_key):
        return {
            "available": False,
            "reason": "no_rows_for_session",
            "data": [],
            "metadata": {},
        }

    events: list[TimelineEvent] = []
    race_control_rows = conn.execute(
        """
        SELECT rc.date, d.name_acronym, rc.category, rc.flag, rc.message
        FROM fact_race_control rc
        LEFT JOIN dim_drivers d ON rc.driver_number = d.driver_number
        WHERE rc.session_key = ?
        ORDER BY rc.date ASC
        """,
        (session_key,),
    ).fetchall()
    for row in race_control_rows:
        events.append(
            TimelineEvent(
                event_type="race_control",
                timestamp=_format_timestamp(row[0]),
                driver=row[1],
                severity=_severity_for_flag(row[3]),
                source="fact_race_control",
                label=row[4] or row[2] or "Race control event",
                details={"category": row[2], "flag": row[3]},
            )
        )

    pit_rows = conn.execute(
        """
        SELECT p.date, d.name_acronym, p.lap_number, p.stop_duration, p.lane_duration, p.pit_duration
        FROM fact_pit_stops p
        LEFT JOIN dim_drivers d ON p.driver_number = d.driver_number
        WHERE p.session_key = ?
        ORDER BY p.date ASC, p.lap_number ASC
        """,
        (session_key,),
    ).fetchall()
    for row in pit_rows:
        events.append(
            TimelineEvent(
                event_type="pit_stop",
                timestamp=_format_timestamp(row[0]),
                lap_number=row[2],
                driver=row[1],
                source="fact_pit_stops",
                label=f"Pit stop {row[1] or ''}".strip(),
                details={
                    "stop_duration": row[3],
                    "lane_duration": row[4],
                    "pit_duration": row[5],
                },
            )
        )

    overtake_rows = conn.execute(
        """
        SELECT o.date, d1.name_acronym, d2.name_acronym, o.position
        FROM fact_overtakes o
        LEFT JOIN dim_drivers d1 ON o.overtaking_driver_number = d1.driver_number
        LEFT JOIN dim_drivers d2 ON o.overtaken_driver_number = d2.driver_number
        WHERE o.session_key = ?
        ORDER BY o.date ASC
        """,
        (session_key,),
    ).fetchall()
    for row in overtake_rows:
        events.append(
            TimelineEvent(
                event_type="overtake",
                timestamp=_format_timestamp(row[0]),
                driver=row[1],
                source="fact_overtakes",
                label=f"{row[1] or 'Driver'} overtook {row[2] or 'driver'}",
                details={"overtaken_driver": row[2], "position": row[3]},
            )
        )

    events.sort(key=lambda event: event.timestamp or "")
    data = [event.model_dump() for event in events]
    return {
        "available": bool(data),
        "reason": "ok" if data else "no_rows_for_session",
        "data": data,
        "metadata": {"count": len(data)},
    }


def fetch_pipeline_health(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> dict[str, Any]:
    if not _session_exists(conn, session_key):
        return _empty_response(
            "no_rows_for_session", "Sessão não encontrada no lakehouse."
        )

    columns = _table_columns(conn, "fact_pipeline_execution")
    select_columns = [
        _column_or_null(columns, "run_id", "VARCHAR"),
        _column_or_null(columns, "pipeline_name", "VARCHAR"),
        _column_or_null(columns, "session_key", "INTEGER"),
        _column_or_null(columns, "execution_timestamp", "TIMESTAMP"),
        _column_or_null(columns, "duration_seconds", "DOUBLE"),
        _column_or_null(columns, "status", "VARCHAR"),
        _column_or_null(columns, "total_rows_processed", "INTEGER"),
        _column_or_null(columns, "total_rows_bronze", "INTEGER"),
        _column_or_null(columns, "total_rows_silver", "INTEGER"),
        _column_or_null(columns, "total_rows_quarantine", "INTEGER"),
        _column_or_null(columns, "quarantine_rate", "DOUBLE"),
    ]
    rows = conn.execute(
        f"""
        SELECT {", ".join(select_columns)}
        FROM fact_pipeline_execution
        WHERE session_key = ?
        ORDER BY execution_timestamp DESC
        LIMIT 10
        """,
        (session_key,),
    ).fetchall()
    if not rows:
        return _empty_response(
            "pipeline_history_unavailable",
            "Nenhum histórico de execução foi encontrado para esta sessão.",
        )

    history = [
        PipelineExecution(
            run_id=row[0],
            pipeline_name=row[1],
            session_key=row[2],
            execution_timestamp=_format_timestamp(row[3]),
            duration_seconds=row[4],
            status=row[5],
            total_rows_processed=row[6],
            total_rows_bronze=row[7],
            total_rows_silver=row[8],
            total_rows_quarantine=row[9],
            quarantine_rate=row[10],
        )
        for row in rows
    ]
    latest = history[0]
    latest_status = (latest.status or "").upper()
    health_status: Literal["healthy", "warning", "unavailable"] = (
        "healthy"
        if "SUCCESS" in latest_status or "SUCCESS" == latest_status
        else "warning"
    )
    data = PipelineHealthData(
        latest_execution=latest, history=history, health_status=health_status
    )
    return {
        "available": True,
        "reason": "ok",
        "data": data.model_dump(),
        "metadata": {},
    }


def fetch_prediction_status(
    conn: duckdb.DuckDBPyConnection, session_key: int
) -> dict[str, Any]:
    if not _session_exists(conn, session_key):
        return _empty_response(
            "no_rows_for_session", "Sessão não encontrada no lakehouse."
        )

    row = conn.execute(
        """
        SELECT COUNT(*) AS prediction_count,
               COUNT(DISTINCT driver_number) AS driver_count,
               MIN(delta_performance_seconds) AS min_delta,
               MAX(delta_performance_seconds) AS max_delta,
               AVG(delta_performance_seconds) AS avg_delta
        FROM gold_lap_predictions
        WHERE session_key = ?
        """,
        (session_key,),
    ).fetchone()
    prediction_count = int(row[0] or 0)
    if prediction_count == 0:
        data = PredictionStatusData(
            available=False, session_key=session_key, prediction_count=0
        )
        return {
            "available": False,
            "reason": "gold_unavailable",
            "data": data.model_dump(),
            "metadata": {
                "empty_state": {
                    "available": False,
                    "reason": "gold_unavailable",
                    "message": "Predições Gold ainda não foram materializadas para esta sessão.",
                }
            },
        }
    data = PredictionStatusData(
        available=True,
        session_key=session_key,
        prediction_count=prediction_count,
        driver_count=int(row[1] or 0),
        min_delta=row[2],
        max_delta=row[3],
        avg_delta=row[4],
    )
    return {
        "available": True,
        "reason": "ok",
        "data": data.model_dump(),
        "metadata": {},
    }


def fetch_driver_duel(
    conn: duckdb.DuckDBPyConnection, session_key: int, driver_1: int, driver_2: int
) -> dict[str, Any]:
    if not _session_exists(conn, session_key):
        return _empty_response(
            "no_rows_for_session", "Sessão não encontrada no lakehouse."
        )

    metric_rows = conn.execute(
        """
        SELECT driver_number,
               MAX(speed) AS max_speed,
               MAX(rpm) AS max_rpm,
               AVG(CASE WHEN throttle > 90 THEN 1.0 ELSE 0.0 END) * 100 AS full_throttle_pct,
               AVG(CASE WHEN brake > 50 THEN 1.0 ELSE 0.0 END) * 100 AS heavy_brake_pct,
               AVG(CASE WHEN drs > 0 THEN 1.0 ELSE 0.0 END) * 100 AS drs_pct
        FROM fact_car_telemetry
        WHERE session_key = ? AND driver_number IN (?, ?)
        GROUP BY driver_number
        """,
        (session_key, driver_1, driver_2),
    ).fetchall()
    if not metric_rows:
        return _empty_response(
            "no_rows_for_session",
            "Telemetria comparável não encontrada para os pilotos selecionados.",
        )

    pit_rows = conn.execute(
        """
        SELECT driver_number, MIN(pit_duration)
        FROM fact_pit_stops
        WHERE session_key = ? AND driver_number IN (?, ?)
        GROUP BY driver_number
        """,
        (session_key, driver_1, driver_2),
    ).fetchall()
    prediction_rows = conn.execute(
        """
        SELECT driver_number, AVG(delta_performance_seconds)
        FROM gold_lap_predictions
        WHERE session_key = ? AND driver_number IN (?, ?)
        GROUP BY driver_number
        """,
        (session_key, driver_1, driver_2),
    ).fetchall()
    pits = {row[0]: row[1] for row in pit_rows}
    predictions = {row[0]: row[1] for row in prediction_rows}
    drivers = {
        str(row[0]): DuelDriverMetrics(
            driver_number=row[0],
            max_speed=row[1],
            max_rpm=row[2],
            full_throttle_pct=round(row[3] or 0.0, 1),
            heavy_brake_pct=round(row[4] or 0.0, 1),
            drs_pct=round(row[5] or 0.0, 1),
            best_pit=pits.get(row[0]),
            prediction_delta_avg=predictions.get(row[0]),
        ).model_dump()
        for row in metric_rows
    }
    try:
        point_rows = conn.execute(
            """
            SELECT driver_number, x, y, speed, n_gear
            FROM fact_car_telemetry
            WHERE session_key = ? AND driver_number IN (?, ?) AND x IS NOT NULL AND y IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (PARTITION BY driver_number ORDER BY date ASC) <= 100
            ORDER BY driver_number, date ASC
            """,
            (session_key, driver_1, driver_2),
        ).fetchall()
    except duckdb.BinderException:
        point_rows = []
    data = DriverDuelData(
        session_key=session_key,
        drivers=drivers,
        sample_points=[
            DuelPoint(
                driver_number=row[0], x=row[1], y=row[2], speed=row[3], gear=row[4]
            )
            for row in point_rows
        ],
    )
    return {
        "available": True,
        "reason": "ok",
        "data": data.model_dump(),
        "metadata": {},
    }


@router.get("/session_summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_key: int = Query(...), db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    return await run_query_async(fetch_session_summary, db, session_key)


@router.get("/driver_options", response_model=DriverOptionsResponse)
async def get_driver_options(
    session_key: int = Query(...), db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    return await run_query_async(fetch_driver_options, db, session_key)


@router.get("/strategy_timeline", response_model=TimelineResponse)
async def get_strategy_timeline(
    session_key: int = Query(...), db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    return await run_query_async(fetch_strategy_timeline, db, session_key)


@router.get("/pipeline_health", response_model=PipelineHealthResponse)
async def get_pipeline_health(
    session_key: int = Query(...), db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    return await run_query_async(fetch_pipeline_health, db, session_key)


@router.get("/prediction_status", response_model=PredictionStatusResponse)
async def get_prediction_status(
    session_key: int = Query(...), db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    return await run_query_async(fetch_prediction_status, db, session_key)


@router.get("/driver_duel", response_model=DriverDuelResponse)
async def get_driver_duel(
    session_key: int = Query(...),
    driver_1: int = Query(...),
    driver_2: int = Query(...),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    return await run_query_async(fetch_driver_duel, db, session_key, driver_1, driver_2)
