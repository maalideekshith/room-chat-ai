from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator

Provider = Literal["openai", "anthropic", "gemini"]


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)
    provider: Provider | None = None
    credential_id: UUID | None = None
    model: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=160)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value


class ConversationSettings(BaseModel):
    provider: Provider | None = None
    credential_id: UUID | None = None
    model: str | None = Field(default=None, min_length=1, max_length=100)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    provider: str | None = Field(validation_alias=AliasChoices("provider", "ai_provider"))
    credential_id: UUID | None = Field(
        validation_alias=AliasChoices("credential_id", "ai_credential_id")
    )
    model: str | None = Field(validation_alias=AliasChoices("model", "ai_model"))
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    source_refs: list[str]
    created_at: datetime


class CredentialCreate(BaseModel):
    provider: Provider
    label: str = Field(min_length=1, max_length=80)
    api_key: SecretStr = Field(min_length=8, max_length=512)

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Credential label cannot be blank")
        return value


class CredentialReplace(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    api_key: SecretStr | None = Field(default=None, min_length=8, max_length=512)


class CredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    label: str
    key_suffix: str
    status: str
    last_validated_at: datetime | None
    created_at: datetime


class PreferencesUpdate(BaseModel):
    provider: Provider | None = None
    credential_id: UUID | None = None
    model: str | None = Field(default=None, min_length=1, max_length=100)


class PreferencesResponse(BaseModel):
    provider: str | None
    credential_id: UUID | None
    model: str | None


class UrlSourceCreate(BaseModel):
    url: HttpUrl


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    title: str
    url: str | None
    mime_type: str | None
    size_bytes: int | None
    status: str
    error_code: str | None
    created_at: datetime
    processed_at: datetime | None
