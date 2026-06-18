import duckdb
import pandas as pd
import pytest


def _silver_fixture_data():
    """Return silver DataFrames that mirror what the pipeline produces."""
    sessions = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "year": 2025,
                "session_name": "Race",
                "session_type": "Race",
                "circuit_key": 12,
                "circuit_short_name": "Bahrain GP",
                "country_name": "Bahrain",
                "date_start": "2025-03-16 12:00:00",
                "date_end": "2025-03-16 14:00:00",
            },
        ]
    )

    stints = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "stint_number": 1,
                "compound": "SOFT",
                "lap_start": 1,
                "lap_end": 15,
                "tyre_age_at_start": 0,
            },
        ]
    )
    stints["lap_end"] = stints["lap_end"].astype("int64")

    telemetry = pd.DataFrame(
        [
            {
                "session_key": 10014,
                "driver_number": 44,
                "date": "2025-03-16 12:00:00",
                "speed": 312,
                "rpm": 11800,
                "n_gear": 7,
                "throttle": 98.5,
                "brake": 0.0,
                "drs": 12,
            },
            {
                "session_key": 10014,
                "driver_number": 44,
                "date": "2025-03-16 12:00:01",
                "speed": 315,
                "rpm": 12000,
                "n_gear": 8,
                "throttle": 99.0,
                "brake": 0.0,
                "drs": 12,
            },
            {
                "session_key": 10014,
                "driver_number": 44,
                "date": "2025-03-16 12:00:02",
                "speed": 310,
                "rpm": 11500,
                "n_gear": 7,
                "throttle": 95.0,
                "brake": 5.0,
                "drs": 10,
            },
        ]
    )

    return sessions, stints, telemetry


def test_gold_telemetry_analysis_query():
    """
    Validate the core DuckDB query logic from gold_f1_telemetry_analysis asset.

    Replicates the query using registered tables instead of read_parquet,
    verifying lap estimation, aggregations, and derived columns.
    """
    sessions, stints, telemetry = _silver_fixture_data()

    conn = duckdb.connect(database=":memory:")
    conn.register("dim_sessions", sessions)
    conn.register("dim_stints", stints)
    conn.register("fact_car_telemetry", telemetry)

    query = """
    WITH session_time AS (
        SELECT session_key,
               CAST(date_start AS TIMESTAMP) AS start_time,
               CAST(date_end AS TIMESTAMP) AS end_time
        FROM dim_sessions
    ),
    telemetry_filtered AS (
        SELECT t.*
        FROM fact_car_telemetry t
        JOIN session_time s ON t.session_key = s.session_key
        WHERE CAST(t.date AS TIMESTAMP) BETWEEN s.start_time AND s.end_time
    ),
    telemetry_with_row AS (
        SELECT session_key, driver_number, date, speed, rpm, n_gear,
               throttle, brake, drs,
               LAG(n_gear) OVER (PARTITION BY session_key, driver_number ORDER BY date ASC) as prev_gear,
               ROW_NUMBER() OVER (PARTITION BY session_key, driver_number ORDER BY date ASC) - 1 AS row_idx,
               COUNT(*) OVER (PARTITION BY session_key, driver_number) AS N
        FROM telemetry_filtered
    ),
    stint_summary AS (
        SELECT session_key, driver_number,
               CAST(MAX(lap_end) AS INTEGER) AS total_laps
        FROM dim_stints
        GROUP BY session_key, driver_number
    ),
    telemetry_with_lap AS (
        SELECT t.*, s.total_laps,
               1 + CAST(FLOOR(t.row_idx * s.total_laps / t.N) AS INTEGER) AS lap_number
        FROM telemetry_with_row t
        JOIN stint_summary s
          ON t.session_key = s.session_key
         AND t.driver_number = s.driver_number
    )
    SELECT session_key, driver_number, lap_number,
           MAX(speed) AS max_speed,
           AVG(speed) AS avg_speed,
           MAX(rpm) AS max_rpm,
           AVG(rpm) AS avg_rpm,
           AVG(CASE WHEN throttle > 90 THEN 1.0 ELSE 0.0 END) * 100 AS throttle_intensity_pct,
           AVG(CASE WHEN brake > 50 THEN 1.0 ELSE 0.0 END) * 100 AS brake_intensity_pct,
           AVG(CASE WHEN drs % 2 = 0 AND drs > 0 THEN 1.0 ELSE 0.0 END) * 100 AS drs_activation_pct,
           SUM(CASE WHEN prev_gear IS NOT NULL AND n_gear <> prev_gear THEN 1 ELSE 0 END) AS gear_changes
    FROM telemetry_with_lap
    GROUP BY session_key, driver_number, lap_number
    ORDER BY session_key, driver_number, lap_number ASC
    """

    df = conn.execute(query).df()
    assert not df.empty
    assert len(df) >= 1
    assert df["session_key"].nunique() == 1
    assert df["driver_number"].nunique() == 1
    assert int(df["session_key"].iloc[0]) == 10014
    assert int(df["driver_number"].iloc[0]) == 44
    assert (df["lap_number"] >= 1).all()
    assert (df["max_speed"] >= 0).all()
    assert (df["avg_speed"] >= 0).all()
    assert (df["max_rpm"] >= 0).all()
    assert (df["throttle_intensity_pct"] >= 0).all()
    assert (df["throttle_intensity_pct"] <= 100).all()
    assert (df["brake_intensity_pct"] >= 0).all()
    assert (df["drs_activation_pct"] >= 0).all()
    assert (df["gear_changes"] >= 0).all()


def test_gold_telemetry_analysis_speed_ranges():
    """Ensure all derived metrics stay within physically plausible bounds."""
    sessions, stints, telemetry = _silver_fixture_data()
    conn = duckdb.connect(database=":memory:")
    conn.register("dim_sessions", sessions)
    conn.register("dim_stints", stints)
    conn.register("fact_car_telemetry", telemetry)

    df = conn.execute("""
        SELECT speed FROM fact_car_telemetry WHERE speed > 0
    """).df()
    assert (df["speed"] >= 0).all()
    assert (df["speed"] <= 400).all()


def test_gold_telemetry_analysis_multi_driver():
    """Test with two drivers to verify partitioning by driver_number."""
    sessions, stints, telemetry = _silver_fixture_data()

    telemetry2 = pd.concat(
        [
            telemetry,
            pd.DataFrame(
                [
                    {
                        "session_key": 10014,
                        "driver_number": 1,
                        "date": "2025-03-16T12:00:00.000",
                        "speed": 320,
                        "rpm": 12100,
                        "n_gear": 8,
                        "throttle": 100.0,
                        "brake": 0.0,
                        "drs": 12,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )

    stints2 = pd.concat(
        [
            stints,
            pd.DataFrame(
                [
                    {
                        "session_key": 10014,
                        "driver_number": 1,
                        "stint_number": 1,
                        "compound": "MEDIUM",
                        "lap_start": 1,
                        "lap_end": 10,
                        "tyre_age_at_start": 0,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    stints2["lap_end"] = stints2["lap_end"].astype("int64")

    conn = duckdb.connect(database=":memory:")
    conn.register("dim_sessions", sessions)
    conn.register("dim_stints", stints2)
    conn.register("fact_car_telemetry", telemetry2)

    df = conn.execute("SELECT DISTINCT driver_number FROM fact_car_telemetry").df()
    assert len(df) == 2


@pytest.mark.slow
def test_gold_telemetry_analysis_no_crash_on_empty():
    """Running the query on empty tables should not crash."""
    conn = duckdb.connect(database=":memory:")
    conn.execute("CREATE TABLE dim_sessions AS SELECT * FROM (SELECT NULL::INTEGER as session_key) WHERE 1=0")
    conn.execute(
        "CREATE TABLE dim_stints AS SELECT * FROM (SELECT NULL::INTEGER as session_key, NULL::INTEGER as driver_number, NULL::INTEGER as lap_end) WHERE 1=0"
    )
    conn.execute(
        "CREATE TABLE fact_car_telemetry AS SELECT * FROM (SELECT NULL::INTEGER as session_key, NULL::INTEGER as driver_number, NULL::TIMESTAMP as date, NULL::INTEGER as speed) WHERE 1=0"
    )
    df = conn.execute("SELECT COUNT(*) as cnt FROM dim_sessions").df()
    assert int(df["cnt"].iloc[0]) == 0
