import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base directory of the project
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    # Path to the DuckDB Silver database file
    DATABASE_PATH: str = os.path.join(BASE_DIR, "data/silver/openf1_silver.duckdb")

    # Configuration prefix
    model_config = SettingsConfigDict(env_prefix="OPENF1_")


settings = Settings()
