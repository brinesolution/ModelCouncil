from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="MODEL_COUNCIL_ENV")
    log_level: str = Field(default="INFO", alias="MODEL_COUNCIL_LOG_LEVEL")

    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")
    deepseek_thinking: str = Field(default="disabled", alias="DEEPSEEK_THINKING")

    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    web_origin: str = Field(default="http://localhost:3000", alias="WEB_ORIGIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
