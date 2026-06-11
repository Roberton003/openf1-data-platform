from datetime import datetime
from typing import Optional

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
    country_code: Optional[str] = Field(
        None, description="Código de país do piloto (ex: GBR, MON)"
    )


class RaceControlContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessão vinculada")
    driver_number: Optional[int] = Field(
        None, description="Número do piloto envolvido, se aplicável"
    )
    category: str = Field(..., description="Categoria do evento de pista")
    flag: Optional[str] = Field(
        None, description="Bandeira exibida (ex: GREEN, RED, YELLOW)"
    )
    message: str = Field(..., description="Mensagem oficial do controle de prova")
    date: datetime = Field(..., description="Timestamp do incidente")


class SessionResultContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessão")
    driver_number: int = Field(..., description="Número do piloto")
    position: Optional[int] = Field(None, description="Posição final obtida")
    number_of_laps: Optional[int] = Field(
        None, description="Número de voltas completadas"
    )
    points: Optional[float] = Field(None, description="Pontos obtidos")
    dnf: Optional[bool] = Field(None, description="Did Not Finish")
    dns: Optional[bool] = Field(None, description="Did Not Start")
    dsq: Optional[bool] = Field(None, description="Disqualified")
    duration: Optional[float] = Field(None, description="Tempo total de corrida")
    gap_to_leader: Optional[str] = Field(
        None, description="Tempo de gap para o líder da prova"
    )


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
