"""Environment-backed application configuration."""

import os
import re
from decimal import Decimal
from functools import lru_cache
from importlib.util import find_spec
from typing import Literal
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, HttpUrl, SecretStr, field_validator, model_validator
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
    resend_api_key: SecretStr | None = None
    resend_from_email: str | None = None
    support_email: str | None = None
    resend_domain_verified: bool = False
    email_worker_poll_seconds: int = Field(default=10, ge=1, le=3600)
    email_max_attempts: int = Field(default=8, ge=1, le=20)
    password_reset_redirect_url: HttpUrl | None = None
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0, le=1)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/salon_platform"
    db_ssl_ca_file: str | None = None
    db_ssl_strict: bool = True

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
    # Used by the validated backend image upload gateway.
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

    # Processed storage policy; originals are bounded separately by the HTTP contract.
    image_max_pixels: int = Field(default=40_000_000, ge=1, le=40_000_000)
    image_avatar_dimension: int = Field(default=512, ge=1, le=4096)
    image_staff_dimension: int = Field(default=1024, ge=1, le=4096)
    image_gallery_dimension: int = Field(default=1600, ge=1, le=4096)
    image_avatar_max_bytes: int = Field(default=512000, ge=1, le=5242880)
    image_photo_max_bytes: int = Field(default=1048576, ge=1, le=5242880)
    media_cleanup_grace_seconds: int = Field(default=86400, ge=3600)
    media_cleanup_interval_seconds: int = Field(default=3600, ge=60)

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

    # Account deletion. The secret keys the HMAC of OTP-bound contacts, confirmation
    # tokens and status tokens. Unset => deletion endpoints answer 503 outside local/test.
    account_deletion_secret: str | None = Field(default=None, min_length=32)
    account_deletion_challenge_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    account_deletion_confirmation_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    account_deletion_resend_cooldown_seconds: int = Field(default=60, ge=10, le=3600)
    account_deletion_max_attempts: int = Field(default=5, ge=1, le=10)
    account_deletion_max_resends: int = Field(default=3, ge=0, le=10)
    account_deletion_max_challenges_per_hour: int = Field(default=5, ge=1, le=50)
    account_deletion_worker_poll_seconds: int = Field(default=15, ge=1, le=3600)
    account_deletion_stale_processing_seconds: int = Field(default=600, ge=60)
    # Claims after which a still-unsettled (or un-issuable) closure refund is recorded as
    # failed/left for the operator and erasure proceeds. Backoff makes 8 claims ~3 hours.
    account_deletion_refund_max_attempts: int = Field(default=8, ge=1, le=50)

    # Owner subscription billing provider ('none' = no external calls, billing endpoints answer
    # 503, no checkout). Any other value names an adapter module in
    # app/infrastructure/subscriptions/. INDEPENDENT of PAYMENT_PROVIDER: a subscription outage
    # never disables booking collection and vice versa.
    subscription_provider: str = "none"
    # Subscription credentials, deliberately separate from the booking RAZORPAY_* settings.
    subscription_razorpay_key_id: str | None = None
    subscription_razorpay_key_secret: SecretStr | None = None
    # Days an expired period keeps the promotion benefit. NO default (a commercial rule):
    # required when the provider is enabled; 0 is a valid explicit "no grace".
    subscription_grace_days: int | None = Field(default=None, ge=0, le=90)
    # Explicit acknowledgement required before LIVE (rzp_live_) keys can be used.
    subscription_allow_live: bool = False
    # How long an unpaid checkout order stays open locally before the sweep expires it.
    subscription_order_ttl_seconds: int = Field(default=3600, ge=300, le=86400)
    # Age of an open (created/authorized) billing row before the worker asks the provider.
    subscription_reconcile_after_seconds: int = Field(default=600, ge=60, le=86400)

    # Customer payment collection. 'none' = dormant: GET /v1/payments/config answers
    # enabled=false, money endpoints answer 503, and no webhook route is registered.
    # Any other value names an adapter module in app/infrastructure/payments/.
    payment_provider: str = "none"
    # 'platform_collect' = provider-side split settlement (funds stay in the provider's
    # escrow; the provider splits to each salon's linked account). 'direct_to_salon' is
    # reserved for per-salon credentials, which do not exist yet, so boot refuses it.
    payment_settlement_model: str = "platform_collect"
    payment_currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    # Share of the booking total taken up front by "Pay advance".
    payment_advance_percent: int = Field(default=30, ge=1, le=100)
    payment_intent_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    payment_idempotency_ttl_seconds: int = Field(default=86400, ge=60, le=604800)
    payment_webhook_max_body_bytes: int = Field(default=262144, ge=1024, le=4194304)
    payment_webhook_max_attempts: int = Field(default=8, ge=1, le=50)
    # Commission policy. NO default: the commercial rule is not approved, so a real provider
    # with platform_collect refuses to boot until both are set deliberately.
    payment_platform_fee_percent: Decimal | None = Field(default=None, ge=0, le=100)
    payment_commission_base: Literal["online_amount", "booking_total"] | None = None
    # The SALON bears the payment gateway fee (never shown to customers). Snapshotted per
    # payment at intent time and deducted from the Easy Split payee share.
    payment_gateway_fee_percent: Decimal = Field(default=Decimal("2.0"), ge=0, le=100)
    # Customer-initiated cancellation of a PAID-ONLINE booking keeps this deduction. The owner
    # still has to confirm Rs 10 flat vs 10 percent, so both are supported.
    cancellation_deduction_type: Literal["percent", "flat"] = "percent"
    cancellation_deduction_value: Decimal = Field(default=Decimal("10.00"), ge=0)
    # Cancellation refunds whose provider call failed are re-driven by the payment worker this
    # many times (with the SAME refund id) before an ERROR + anomaly row asks for a human.
    payment_refund_max_attempts: int = Field(default=8, ge=1, le=50)
    # Free-text label stamped on every snapshot; bump it when the rule changes.
    payment_commission_policy_version: str = Field(default="1", min_length=1, max_length=40)
    # Explicit acknowledgement required before any LIVE (production) provider environment can
    # be used. Default off: live activation fails closed.
    payment_allow_live: bool = False
    payment_worker_poll_seconds: int = Field(default=10, ge=1, le=3600)
    payment_reconcile_after_seconds: int = Field(default=600, ge=60, le=86400)
    # Razorpay credentials (used only when PAYMENT_PROVIDER=razorpay).
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    razorpay_route_enabled: bool = False
    razorpay_api_base_url: str = "https://api.razorpay.com/v1"
    # Owner subscriptions use their OWN webhook secret, independent of the booking-payment
    # provider. Webhooks signed with it are verified, stored and applied by the subscription
    # billing use cases (only when SUBSCRIPTION_PROVIDER is enabled).
    subscription_razorpay_webhook_secret: SecretStr | None = None
    # Cashfree PG + Easy Split (used only when PAYMENT_PROVIDER=cashfree).
    cashfree_enabled: bool = False
    cashfree_client_id: str | None = Field(default=None, validation_alias=AliasChoices("CASHFREE_APP_ID", "cashfree_client_id"))
    cashfree_client_secret: SecretStr | None = Field(default=None, validation_alias=AliasChoices("CASHFREE_SECRET_KEY", "cashfree_client_secret"))
    cashfree_environment: Literal["sandbox", "production"] = Field(default="sandbox", validation_alias=AliasChoices("CASHFREE_ENV", "cashfree_environment"))
    cashfree_api_version: str = Field(default="2026-01-01", min_length=8, max_length=20)
    cashfree_webhook_version: str = Field(default="2025-01-01", min_length=8, max_length=20)
    cashfree_easy_split_enabled: bool = False
    cashfree_return_url: str | None = Field(default=None, max_length=250)
    # Maximum clock skew accepted between x-webhook-timestamp and now (replay window).
    # Authenticity is the HMAC; replays are stopped by per-provider event-id dedupe. Cashfree retries
    # for a long time and may reuse the original timestamp, so a tight window would drop real retries.
    cashfree_webhook_tolerance_seconds: int = Field(default=86400, ge=60, le=86400)
    # Outbound provider calls: seconds before a call is treated as an unknown outcome.
    payment_provider_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    # Worker pass that would release unpaid bookings after payment failure/expiry. NOT built:
    # accepted only as false so a deployment cannot believe it is enabled.
    payment_auto_release_enabled: bool = False

    # Database connection pool
    db_pool_size: int = Field(default=5, ge=1, le=100)
    db_max_overflow: int = Field(default=5, ge=0, le=100)
    db_pool_timeout_seconds: int = Field(default=10, ge=1, le=120)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    db_connect_timeout_seconds: float = Field(default=10, gt=0, le=120)

    @field_validator("account_deletion_secret", mode="before")
    @classmethod
    def blank_account_deletion_secret_is_unset(cls, value: object) -> object:
        """Allow unfilled env templates; deletion still requires a configured secret."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("password_reset_redirect_url", "resend_from_email", "support_email", mode="before")
    @classmethod
    def blank_optional_email_setting_is_unset(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("subscription_grace_days", mode="before")
    @classmethod
    def blank_grace_is_unset(cls, value: object) -> object:
        """``SUBSCRIPTION_GRACE_DAYS=`` means "not decided", never zero."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("payment_platform_fee_percent", "payment_commission_base", mode="before")
    @classmethod
    def blank_commission_is_unset(cls, value: object) -> object:
        """``KEY=`` in an env template means "not decided", never zero."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

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
    def validate_payment_settings(self) -> "Settings":
        """Refuse illegal payment configurations in every environment.

        Kept apart from ``validate_production_settings`` so that a half-configured
        provider fails the boot in local/test too, not only in production.
        """

        self.payment_provider = (self.payment_provider or "none").strip().lower()
        if self.payment_provider != "none":
            if not re.fullmatch(r"[a-z][a-z0-9_]*", self.payment_provider):
                raise ValueError("PAYMENT_PROVIDER must be 'none' or an adapter module name")
            if find_spec(f"app.infrastructure.payments.{self.payment_provider}") is None:
                raise ValueError(
                    f"PAYMENT_PROVIDER={self.payment_provider!r} has no adapter in "
                    "app/infrastructure/payments/"
                )
        if self.payment_settlement_model not in {"platform_collect", "direct_to_salon"}:
            raise ValueError("PAYMENT_SETTLEMENT_MODEL must be platform_collect or direct_to_salon")
        if self.payment_settlement_model == "direct_to_salon":
            # Customers paying each salon's own provider account needs a per-salon
            # credential store, which is not built.
            raise ValueError(
                "PAYMENT_SETTLEMENT_MODEL=direct_to_salon is not available until per-salon "
                "provider credentials exist"
            )
        if self.payment_provider == "razorpay":
            problems = [
                name
                for name, value in {
                    "RAZORPAY_KEY_ID": self.razorpay_key_id,
                    "RAZORPAY_KEY_SECRET": self.razorpay_key_secret,
                    "RAZORPAY_WEBHOOK_SECRET": self.razorpay_webhook_secret,
                }.items()
                if not value
            ]
            if problems:
                raise ValueError(
                    "PAYMENT_PROVIDER=razorpay is missing: " + ", ".join(problems)
                )
            if self.payment_settlement_model == "platform_collect" and not self.razorpay_route_enabled:
                raise ValueError(
                    "PAYMENT_SETTLEMENT_MODEL=platform_collect requires RAZORPAY_ROUTE_ENABLED=true "
                    "(collecting into the platform's own account without split settlement would "
                    "make the platform a payment aggregator)"
                )
        if self.payment_provider == "cashfree" and self.cashfree_enabled:
            problems = [
                name
                for name, value in {
                    "CASHFREE_CLIENT_ID": self.cashfree_client_id,
                    "CASHFREE_CLIENT_SECRET": (
                        self.cashfree_client_secret.get_secret_value()
                        if self.cashfree_client_secret
                        else None
                    ),
                }.items()
                if not value
            ]
            if problems:
                raise ValueError("PAYMENT_PROVIDER=cashfree is missing: " + ", ".join(problems))
            if self.cashfree_environment == "production" and not self.payment_allow_live:
                raise ValueError(
                    "CASHFREE_ENVIRONMENT=production requires PAYMENT_ALLOW_LIVE=true "
                    "(live activation is an explicit, reviewed decision)"
                )
        if self.payment_provider == "razorpay" and (self.razorpay_key_id or "").startswith(
            "rzp_live_"
        ) and not self.payment_allow_live:
            raise ValueError("A live Razorpay key requires PAYMENT_ALLOW_LIVE=true")
        if self.booking_payments_enabled and self.payment_settlement_model == "platform_collect":
            missing = [
                name
                for name, value in {
                    "PAYMENT_PLATFORM_FEE_PERCENT": self.payment_platform_fee_percent,
                    "PAYMENT_COMMISSION_BASE": self.payment_commission_base,
                }.items()
                if value is None
            ]
            if missing:
                raise ValueError(
                    "A real PAYMENT_PROVIDER with platform_collect needs an approved commission "
                    "policy; missing: " + ", ".join(missing) + " (there is deliberately no default)"
                )
        if self.cancellation_deduction_type == "percent" and self.cancellation_deduction_value > 100:
            raise ValueError("CANCELLATION_DEDUCTION_VALUE must be at most 100 for a percent rule")
        if self.payment_auto_release_enabled:
            raise ValueError(
                "PAYMENT_AUTO_RELEASE_ENABLED is not built: failed/expired payments never release a "
                "booking automatically (see PAYMENT_DECISIONS.md)"
            )
        return self

    @property
    def media_bucket(self) -> str:
        """R2 bucket for uploaded media, defaulting to the standard bucket name."""
        return self.r2_bucket or "salon-images"

    @property
    def booking_payments_enabled(self) -> bool:
        return self.payment_provider != "none" and (
            self.payment_provider != "cashfree" or self.cashfree_enabled
        )

    @model_validator(mode="after")
    def validate_subscription_settings(self) -> "Settings":
        """Fail closed on any half-configured or live-by-accident subscription billing."""

        self.subscription_provider = (self.subscription_provider or "none").strip().lower()
        secret = self.subscription_razorpay_webhook_secret
        if secret is not None and secret.get_secret_value() and len(secret.get_secret_value()) < 32:
            raise ValueError("SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET must be at least 32 characters")
        provider = self.subscription_provider
        if provider == "none":
            return self
        if not re.fullmatch(r"[a-z][a-z0-9_]*", provider):
            raise ValueError("SUBSCRIPTION_PROVIDER must be 'none' or an adapter module name")
        if find_spec(f"app.infrastructure.subscriptions.{provider}") is None:
            raise ValueError(
                f"SUBSCRIPTION_PROVIDER={provider!r} has no adapter in "
                "app/infrastructure/subscriptions/"
            )
        if provider == "razorpay":
            problems = [
                name
                for name, value in {
                    "SUBSCRIPTION_RAZORPAY_KEY_ID": self.subscription_razorpay_key_id,
                    "SUBSCRIPTION_RAZORPAY_KEY_SECRET": (
                        self.subscription_razorpay_key_secret.get_secret_value()
                        if self.subscription_razorpay_key_secret
                        else None
                    ),
                    "SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET": (
                        secret.get_secret_value() if secret else None
                    ),
                }.items()
                if not value
            ]
            if problems:
                raise ValueError(
                    "SUBSCRIPTION_PROVIDER=razorpay is missing: " + ", ".join(problems)
                )
            if (self.subscription_razorpay_key_id or "").startswith("rzp_live_") and not (
                self.subscription_allow_live
            ):
                raise ValueError("A live Razorpay key requires SUBSCRIPTION_ALLOW_LIVE=true")
        if self.subscription_grace_days is None:
            raise ValueError(
                "SUBSCRIPTION_GRACE_DAYS must be set when SUBSCRIPTION_PROVIDER is enabled "
                "(0 means no grace; there is deliberately no default)"
            )
        return self

    @property
    def subscription_webhook_provider(self) -> str | None:
        """Provider whose subscription webhooks are accepted (None = no subscription hook)."""

        # The validator guarantees that an enabled provider has its webhook secret.
        return None if self.subscription_provider == "none" else self.subscription_provider

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

    return Settings(_env_file=os.environ.get("SALON_ENV_FILE", ".env"))


settings = get_settings()
