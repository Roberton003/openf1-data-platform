import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base directory of the project
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    # Path to the DuckDB Silver database file
    DATABASE_PATH: str = os.path.join(BASE_DIR, "data/silver/openf1_silver.duckdb")

    # GitHub API integration config
    GITHUB_REPO: str = "Roberton003/openf1-data-platform"
    GITHUB_TOKEN: str = ""

    # SMTP Server configurations for alerts
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    ALERT_EMAIL_RECEIVER: str = ""

    # Auto-Healing switch
    AUTO_HEAL_CI: bool = True

    # Configuration prefix
    model_config = SettingsConfigDict(env_prefix="OPENF1_")


settings = Settings()
