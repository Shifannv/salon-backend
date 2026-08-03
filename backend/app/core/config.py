"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings validated at process boot."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Salon Platform API"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/salon_platform"
    supabase_url: HttpUrl | None = None
    supabase_anon_key: str | None = None
    supabase_jwks_url: HttpUrl | None = None
    supabase_jwt_audience: str | None = "authenticated"
    backend_cors_origins: list[str] = Field(default_factory=list)
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout_seconds: int = 10

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Fail fast in non-local environments when provider config is missing."""

        if self.environment not in {"local", "test"}:
            missing = [
                name
                for name, value in {
                    "SUPABASE_URL": self.supabase_url,
                    "SUPABASE_ANON_KEY": self.supabase_anon_key,
                    "SUPABASE_JWKS_URL": self.supabase_jwks_url,
                }.items()
                if not value
            ]
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"Missing required production settings: {joined}")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""

    return Settings()


settings = get_settings()
