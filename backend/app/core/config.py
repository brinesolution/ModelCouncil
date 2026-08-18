from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
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
    deepseek_live_enabled: bool = Field(default=False, alias="DEEPSEEK_LIVE_ENABLED")
    deepseek_render_concurrency: int = Field(
        default=4, ge=1, le=12, alias="DEEPSEEK_RENDER_CONCURRENCY"
    )
    deepseek_full_live_concurrency: int = Field(
        default=4, ge=1, le=12, alias="DEEPSEEK_FULL_LIVE_CONCURRENCY"
    )
    deepseek_max_live_requests_per_run: int = Field(
        default=10, ge=0, le=100, alias="DEEPSEEK_MAX_LIVE_REQUESTS_PER_RUN"
    )
    deepseek_cache_prime_requests: int = Field(
        default=2, ge=0, le=10, alias="DEEPSEEK_CACHE_PRIME_REQUESTS"
    )
    deepseek_cache_hit_usd_per_million: float = Field(
        default=0.0028, ge=0, alias="DEEPSEEK_CACHE_HIT_USD_PER_MILLION"
    )
    deepseek_cache_miss_usd_per_million: float = Field(
        default=0.14, ge=0, alias="DEEPSEEK_CACHE_MISS_USD_PER_MILLION"
    )
    deepseek_output_usd_per_million: float = Field(
        default=0.28, ge=0, alias="DEEPSEEK_OUTPUT_USD_PER_MILLION"
    )

    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL"
    )
    ollama_discovery_timeout_seconds: float = Field(
        default=2.0, gt=0, le=30, alias="OLLAMA_DISCOVERY_TIMEOUT_SECONDS"
    )
    ollama_request_timeout_seconds: float = Field(
        default=120.0, gt=0, le=900, alias="OLLAMA_REQUEST_TIMEOUT_SECONDS"
    )
    ollama_num_ctx: int = Field(
        default=2048, ge=512, le=32768, alias="OLLAMA_NUM_CTX"
    )
    ollama_full_live_concurrency: int = Field(
        default=1, ge=1, le=8, alias="OLLAMA_FULL_LIVE_CONCURRENCY"
    )

    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    web_origin: str = Field(default="http://localhost:3000", alias="WEB_ORIGIN")


def resolve_deepseek_api_key(
    settings: Settings,
    *,
    env_file: Path = PROJECT_ROOT / ".env",
) -> str:
    """Prefer the project-root .env key over a stale inherited process key.

    Runtime controls continue to use normal Pydantic settings precedence; this helper
    is intentionally limited to the DeepSeek secret because the project root .env is
    the documented local source of truth for that credential.
    """
    if env_file.exists():
        project_values = dotenv_values(env_file)
        project_key = project_values.get("DEEPSEEK_API_KEY")
        if isinstance(project_key, str) and project_key.strip():
            return project_key.strip()
    return settings.deepseek_api_key.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
