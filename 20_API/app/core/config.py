from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets are supplied through environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Personal AI Quant Trading OS"
    environment: str = Field(default="development")
    live_trading_enabled: bool = Field(default=False)
    api_prefix: str = Field(default="/api/v1")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/quant_trading_os"
    )

    @property
    def live_trading_allowed(self) -> bool:
        """Live execution requires an explicit runtime opt-in."""
        return self.live_trading_enabled and self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
