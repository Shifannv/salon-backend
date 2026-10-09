"""Environment-backed application configuration."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings validated at process boot."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Salon Platform API"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/salon_platform"

    # Supabase Auth (anon / public key — safe for clients)
    supabase_url: HttpUrl | None = None
    supabase_anon_key: str | None = None
    supabase_jwks_url: HttpUrl | None = None
    supabase_jwt_audience: str | None = "authenticated"

    # Supabase Auth Admin (service-role key — never expose to clients)
    supabase_service_role_key: str | None = None
    # Enable after enrolling the existing super-admin account in Supabase TOTP MFA.
    admin_require_mfa: bool = False

    # Cloudflare R2 object storage (S3-compatible)
    # Used to generate presigned PUT URLs for direct client uploads.
    # R2 is opt-in — leave unset to fall back to an unconfigured storage gateway.
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    # Legacy names kept for existing deploy/local env files.
    r2_endpoint_url: str | None = None
    r2_bucket_name: str | None = None
    # Public base URL for delivered objects (e.g. https://pub-xxx.r2.dev or a custom domain).
    # Must NOT have a trailing slash.
    r2_public_url: str | None = None

    # Externally reachable API origin used for absolute owner QR image URLs.
    public_api_base_url: HttpUrl | None = None

    # Firebase Cloud Messaging (service account JSON string)
    firebase_credentials_json: str | None = None

    # Redis (cache, idempotency keys, rate limiting)
    redis_url: str | None = None

    # CORS
    backend_cors_origins: list[str] = Field(default_factory=list)

    # Walk-in QR — URL prefix of the customer-facing web booking route.
    # QR codes encode: <walkin_base_url>/<qr_token>
    walkin_base_url: str = "http://localhost:3000"

    # Customer cancellation policy. Before this cutoff a customer cancellation
    # is immediate; inside the cutoff window it requires salon approval.
    customer_cancellation_cutoff_minutes: int = Field(default=120, ge=0, le=10080)
    allow_late_cancellation_requests: bool = True

    # Subscription provider ('none' = no external payment calls, no webhook routes).
    # Future values: 'stripe', 'razorpay', etc.
    subscription_provider: str = "none"

    # Database connection pool
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout_seconds: int = 10

    @model_validator(mode="after")
    def normalize_legacy_r2_settings(self) -> "Settings":
        """Accept older R2 env names used by earlier deployment setup."""

        if not self.r2_bucket and self.r2_bucket_name:
            self.r2_bucket = self.r2_bucket_name

        if not self.r2_account_id and self.r2_endpoint_url:
            host = urlparse(self.r2_endpoint_url).hostname or ""
            suffix = ".r2.cloudflarestorage.com"
            if host.endswith(suffix):
                self.r2_account_id = host.removesuffix(suffix)

        return self

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
                    "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
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
