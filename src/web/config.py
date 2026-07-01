import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    GITHUB_REPO: str = os.getenv("OPENF1_GITHUB_REPO", "Roberton003/openf1-data-platform")
    GITHUB_TOKEN: str = os.getenv("OPENF1_GITHUB_TOKEN", "")
    SMTP_HOST: str = os.getenv("OPENF1_SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("OPENF1_SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("OPENF1_SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("OPENF1_SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("OPENF1_SMTP_FROM", "")
    ALERT_EMAIL_RECEIVER: str = os.getenv("OPENF1_ALERT_EMAIL_RECEIVER", "")
    AUTO_HEAL_CI: bool = True

    model_config = SettingsConfigDict(env_prefix="OPENF1_")


settings = Settings()
