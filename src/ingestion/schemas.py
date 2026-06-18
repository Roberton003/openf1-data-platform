from datetime import datetime

import pandas as pd
from pydantic import BaseModel, Field, field_validator

# =====================================================================
# 1. Contratos Pydantic para Entidades Estáticas / Pequena Volumetria
# =====================================================================


class SessionContract(BaseModel):
    session_key: int = Field(..., description="Chave única da sessão")
    year: int = Field(..., description="Ano da temporada")
    session_name: str = Field(..., description="Nome da sessão (ex: Race, Qualifying)")
    session_type: str = Field(..., description="Tipo da sessão")
    circuit_key: int = Field(..., description="Chave única do circuito")
    circuit_short_name: str = Field(..., description="Nome abreviado do circuito")
    country_name: str = Field(..., description="Nome do país onde ocorre o GP")

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if v < 2000 or v > 2100:
            raise ValueError("Ano inválido no contrato de dados da F1")
        return v


class DriverContract(BaseModel):
    driver_number: int = Field(..., description="Número oficial do piloto")
    full_name: str = Field(..., description="Nome completo do piloto")
    name_acronym: str = Field(..., description="Acrônimo do piloto (ex: VER, HAM)")
    team_name: str = Field(..., description="Nome da escuderia")
    country_code: str | None = Field(None, description="Código de país do piloto (ex: GBR, MON)")


class RaceControlContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessão vinculada")
    driver_number: int | None = Field(None, description="Número do piloto envolvido, se aplicável")
    category: str = Field(..., description="Categoria do evento de pista")
    flag: str | None = Field(None, description="Bandeira exibida (ex: GREEN, RED, YELLOW)")
    message: str = Field(..., description="Mensagem oficial do controle de prova")
    date: datetime = Field(..., description="Timestamp do incidente")


class SessionResultContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessão")
    driver_number: int = Field(..., description="Número do piloto")
    position: int | None = Field(None, description="Posição final obtida")
    number_of_laps: int | None = Field(None, description="Número de voltas completadas")
    points: float | None = Field(None, description="Pontos obtidos")
    dnf: bool | None = Field(None, description="Did Not Finish")
    dns: bool | None = Field(None, description="Did Not Start")
    dsq: bool | None = Field(None, description="Disqualified")
    duration: float | None = Field(None, description="Tempo total de corrida")
    gap_to_leader: str | None = Field(None, description="Tempo de gap para o líder da prova")


class OvertakeContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessão")
    overtaking_driver_number: int = Field(..., description="Número do piloto que ultrapassou")
    overtaken_driver_number: int = Field(..., description="Número do piloto ultrapassado")
    date: datetime = Field(..., description="Timestamp da ultrapassagem")
    position: int = Field(..., description="Posição no grid após ultrapassagem")


# =====================================================================
# 2. Contratos Vetoriais de Lote (Pandas/PyArrow Type Mappings)
#    Utilizados para validação rápida vetorizada de alta volumetria.
# =====================================================================

# Telemetria Física (car_data) a ~3.7Hz
TELEMETRY_SCHEMA = {
    "session_key": "int64",
    "driver_number": "int64",
    "date": "datetime64[ns]",
    "speed": "int64",
    "rpm": "int64",
    "n_gear": "int64",
    "throttle": "float64",
    "brake": "float64",
    "drs": "int64",
}

# Paradas de Box (pit_stops)
PIT_STOP_SCHEMA = {
    "session_key": "int64",
    "driver_number": "int64",
    "lap_number": "int64",
    "stop_duration": "float64",
    "lane_duration": "float64",
    "pit_duration": "float64",
    "date": "datetime64[ns]",
}

# Distâncias e Gaps (intervals)
INTERVALS_SCHEMA = {
    "session_key": "int64",
    "driver_number": "int64",
    "gap_to_leader": "string",
    "interval": "string",
    "date": "datetime64[ns]",
}

# Estratégia de Pneu (stints)
STINTS_SCHEMA = {
    "session_key": "int64",
    "driver_number": "int64",
    "stint_number": "int64",
    "compound": "string",
    "lap_start": "int64",
    "lap_end": "int64",
    "tyre_age_at_start": "int64",
}

# Condições Climáticas (weather)
WEATHER_SCHEMA = {
    "session_key": "int64",
    "date": "datetime64[ns]",
    "air_temperature": "float64",
    "track_temperature": "float64",
    "humidity": "float64",
    "wind_speed": "float64",
    "rainfall": "int64",
}

# Localização Espacial (location)
LOCATION_SCHEMA = {
    "session_key": "int64",
    "driver_number": "int64",
    "date": "datetime64[ns]",
    "x": "int64",
    "y": "int64",
    "z": "int64",
}

# Resultados de Sessão (session_result)
SESSION_RESULTS_SCHEMA = {
    "session_key": "int64",
    "driver_number": "int64",
    "position": "int64",
    "number_of_laps": "int64",
    "points": "float64",
    "dnf": pd.BooleanDtype(),
    "dns": pd.BooleanDtype(),
    "dsq": pd.BooleanDtype(),
    "duration": "float64",
    "gap_to_leader": "string",
}

# Ultrapassagens (overtakes)
OVERTAKES_SCHEMA = {
    "session_key": "int64",
    "overtaking_driver_number": "int64",
    "overtaken_driver_number": "int64",
    "date": "datetime64[ns]",
    "position": "int64",
}

# =====================================================================
# 3. Gold Layer Constraints
#    Validates physical constraints on Gold tables (NOT NULL, ranges, derivations).
# =====================================================================

GOLD_TABLE_CONSTRAINTS: dict[str, dict] = {
    "fct_f1_telemetry_analysis": {
        "not_null_cols": [
            "session_key",
            "driver_number",
            "lap_number",
            "max_speed",
            "avg_speed",
            "max_rpm",
            "avg_rpm",
            "throttle_intensity_pct",
            "brake_intensity_pct",
            "drs_activation_pct",
            "gear_changes",
        ],
        "range_checks": {
            "lap_number": (1, None),
            "max_speed": (0, 400),
            "avg_speed": (0, 380),
            "max_rpm": (0, 18000),
            "throttle_intensity_pct": (0, 100),
            "brake_intensity_pct": (0, 100),
            "drs_activation_pct": (0, 100),
            "gear_changes": (0, None),
        },
    },
    "gold_features_lap_data": {
        "not_null_cols": [
            "session_key",
            "driver_number",
            "stint_number",
            "lap_number",
            "lap_duration_seconds",
            "max_speed",
            "max_rpm",
            "throttle_intensity_pct",
            "brake_intensity_pct",
        ],
        "range_checks": {
            "lap_number": (1, None),
            "lap_duration_seconds": (30.0, 600.0),
            "max_speed": (0, 400),
            "max_rpm": (0, 18000),
            "throttle_intensity_pct": (0, 100),
            "brake_intensity_pct": (0, 100),
        },
    },
    "gold_lap_predictions": {
        "not_null_cols": [
            "session_key",
            "driver_number",
            "lap_duration_seconds",
            "predicted_lap_duration_seconds",
            "delta_performance_seconds",
        ],
        "range_checks": {
            "lap_duration_seconds": (30.0, 600.0),
            "predicted_lap_duration_seconds": (30.0, 600.0),
            "delta_performance_seconds": (-300.0, 300.0),
        },
    },
}


def validate_gold_constraints(df: pd.DataFrame, table_name: str) -> list[str]:
    """
    Validate a Gold table DataFrame against physical constraints.

    Returns a list of constraint violation messages (empty if compliant).
    """
    constraints = GOLD_TABLE_CONSTRAINTS.get(table_name)
    if constraints is None:
        return [f"Unknown gold table: {table_name}"]

    violations = []

    for col in constraints["not_null_cols"]:
        if col not in df.columns:
            violations.append(f"Missing column: {col}")
        elif df[col].isna().any():
            null_count = int(df[col].isna().sum())
            violations.append(f"Column {col}: {null_count} null values (expected 0)")

    for col, (lo, hi) in constraints["range_checks"].items():
        if col not in df.columns:
            continue
        if lo is not None and (df[col] < lo).any():
            violations.append(f"Column {col}: values below minimum {lo}")
        if hi is not None and (df[col] > hi).any():
            violations.append(f"Column {col}: values above maximum {hi}")

    return violations
