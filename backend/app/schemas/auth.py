import re
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    SecretStr,
    field_validator,
)

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: SecretStr

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "Username must be 3-30 characters using lowercase letters, "
                "digits, or underscores"
            )
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().lower()

    @field_validator("email")
    @classmethod
    def validate_email_length(cls, value: EmailStr) -> EmailStr:
        if len(str(value)) > 320:
            raise ValueError("Email must be at most 320 characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not password.strip():
            raise ValueError("Password must not be whitespace only")
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
            )
        if len(password) > PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"Password must be at most {PASSWORD_MAX_LENGTH} characters"
            )
        return value


class LoginRequest(BaseModel):
    username_or_email: str
    password: SecretStr

    @field_validator("username_or_email", mode="before")
    @classmethod
    def normalize_identifier(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("username_or_email")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value or len(value) > 320:
            raise ValueError("Invalid username or email")
        return value

    @field_validator("password")
    @classmethod
    def limit_login_password_size(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) > PASSWORD_MAX_LENGTH:
            raise ValueError("Password is too long")
        return value


class TokenResponse(BaseModel):
    access_token: str
    csrf_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
