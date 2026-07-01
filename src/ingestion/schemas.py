from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SessionContract(BaseModel):
    session_key: int = Field(..., description="Chave unica da sessao")
    year: int = Field(..., description="Ano da temporada")
    session_name: str = Field(..., description="Nome da sessao")
    session_type: str = Field(..., description="Tipo da sessao")
    circuit_key: int = Field(..., description="Chave do circuito")
    circuit_short_name: str = Field(..., description="Nome abreviado do circuito")
    country_name: str = Field(..., description="Pais do GP")

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        if value < 2000 or value > 2100:
            raise ValueError("Ano invalido no contrato de dados da F1")
        return value


class DriverContract(BaseModel):
    driver_number: int = Field(..., description="Numero oficial do piloto")
    full_name: str = Field(..., description="Nome completo do piloto")
    name_acronym: str = Field(..., description="Acronimo do piloto")
    team_name: str = Field(..., description="Nome da escuderia")
    country_code: str | None = Field(None, description="Codigo de pais")


class RaceControlContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessao")
    driver_number: int | None = Field(None, description="Numero do piloto")
    category: str = Field(..., description="Categoria do evento")
    flag: str | None = Field(None, description="Bandeira exibida")
    message: str = Field(..., description="Mensagem oficial")
    date: datetime = Field(..., description="Timestamp do incidente")


class SessionResultContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessao")
    driver_number: int = Field(..., description="Numero do piloto")
    position: int | None = Field(None, description="Posicao final")
    number_of_laps: int | None = Field(None, description="Voltas completadas")
    points: float | None = Field(None, description="Pontos obtidos")
    dnf: bool | None = Field(None, description="Did Not Finish")
    dns: bool | None = Field(None, description="Did Not Start")
    dsq: bool | None = Field(None, description="Disqualified")
    duration: float | None = Field(None, description="Tempo total")
    gap_to_leader: str | None = Field(None, description="Gap para o lider")


class OvertakeContract(BaseModel):
    session_key: int = Field(..., description="Chave da sessao")
    overtaking_driver_number: int = Field(..., description="Piloto que ultrapassou")
    overtaken_driver_number: int = Field(..., description="Piloto ultrapassado")
    date: datetime = Field(..., description="Timestamp da ultrapassagem")
    position: int = Field(..., description="Posicao apos ultrapassagem")
