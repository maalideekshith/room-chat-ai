import secrets
import base64

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    app_name: str = "Room Chat AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    database_url: str = "postgresql+asyncpg://localhost:5432/room_chat_ai"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: float = Field(default=30.0, gt=0)
    db_connect_timeout: float = Field(default=5.0, gt=0)
    db_echo: bool = False

    jwt_signing_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "room-chat-ai"
    jwt_audience: str = "room-chat-ai-api"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=365)
    refresh_cookie_name: str = "refresh_token"
    csrf_cookie_name: str = "csrf_token"
    auth_cookie_path: str = "/api/v1/auth"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"

    ai_credential_master_key: str | None = None
    solo_storage_path: str = ".data/solo"
    solo_max_upload_bytes: int = Field(default=10_485_760, ge=1024, le=52_428_800)
    ai_provider_timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg:// scheme")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("Only the application-configured HS256 algorithm is supported")
        return value

    @field_validator("jwt_issuer", "jwt_audience", "refresh_cookie_name", "csrf_cookie_name")
    @classmethod
    def require_nonempty_security_setting(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Security settings must not be empty")
        return value

    @field_validator("auth_cookie_samesite")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @field_validator("ai_credential_master_key")
    @classmethod
    def validate_ai_master_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            key = base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            raise ValueError("AI_CREDENTIAL_MASTER_KEY must be base64 encoded") from None
        if len(key) != 32:
            raise ValueError("AI_CREDENTIAL_MASTER_KEY must encode exactly 32 bytes")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        development = self.environment.lower() in {"development", "dev", "test"}
        if not self.jwt_signing_secret:
            if not development:
                raise ValueError("JWT_SIGNING_SECRET is required outside development")
            self.jwt_signing_secret = secrets.token_urlsafe(48)
        if not development:
            if (
                len(self.jwt_signing_secret.encode("utf-8")) < 32
                or self.jwt_signing_secret.lower().startswith(("replace-with-", "change-me"))
            ):
                raise ValueError("Production requires a non-development JWT secret of at least 32 bytes")
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be enabled outside development")
            if not self.ai_credential_master_key:
                raise ValueError("AI_CREDENTIAL_MASTER_KEY is required outside development")
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError("SameSite=None cookies require AUTH_COOKIE_SECURE=true")
        if self.refresh_cookie_name == self.csrf_cookie_name:
            raise ValueError("Refresh and CSRF cookie names must be different")
        return self


settings = Settings()
