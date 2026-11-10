from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "StaleCheck API"
    version: str = "1.0.0"
    env: str = "dev"

    data_dir: Path = Path("./data")
    database_path: Path | None = None
    api_key: str | None = None
    cors_origins: str = "*"

    llm_provider: str = "mock"
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None

    tavily_api_key: str | None = None
    tavily_base_url: str = "https://api.tavily.com"

    max_claims: int = 10
    max_judged_claims: int = 6
    cache_ttl_seconds: int = 86_400
    request_timeout: float = 30.0

    @property
    def db_path(self) -> Path:
        if self.database_path is not None:
            return self.database_path
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "stalecheck.db"

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
