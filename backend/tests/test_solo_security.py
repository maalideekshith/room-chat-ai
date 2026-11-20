import asyncio
import base64
import socket

import pytest
from cryptography.exceptions import InvalidTag

from app.ai import encryption
from app.ai.providers import GeminiAdapter, ProviderFailure
from app.models.solo import AiCredential
from app.schemas.solo import CredentialResponse
from app.solo.ingestion import (
    IngestionFailure,
    _assert_public_host,
    chunk_text,
    extract_file_text,
    fetch_url_text,
    validate_file,
)


def test_provider_key_envelope_encryption_round_trip_and_integrity(monkeypatch) -> None:
    monkeypatch.setattr(
        encryption.settings,
        "ai_credential_master_key",
        base64.b64encode(b"a" * 32).decode("ascii"),
    )
    encrypted_dek, encrypted_key = encryption.encrypt_api_key("provider-secret-123")
    assert b"provider-secret-123" not in encrypted_dek + encrypted_key
    assert encryption.decrypt_api_key(encrypted_dek, encrypted_key) == "provider-secret-123"
    corrupted = encrypted_key[:-1] + bytes([encrypted_key[-1] ^ 1])
    with pytest.raises(InvalidTag):
        encryption.decrypt_api_key(encrypted_dek, corrupted)


def test_credential_response_contains_metadata_but_never_key_material() -> None:
    credential = AiCredential(
        id="25a1e8ad-8a42-43b7-804c-6f228a85b97b",
        user_id="9ea67bac-9e45-4728-85a0-842e69c22e2c",
        provider="openai",
        label="Personal",
        encrypted_dek=b"encrypted data key",
        encrypted_key=b"encrypted provider key",
        key_suffix="4321",
        status="active",
        created_at="2026-11-21T12:00:00Z",
        last_validated_at=None,
        revoked_at=None,
    )
    response = CredentialResponse.model_validate(credential)
    serialized = response.model_dump_json()
    assert response.key_suffix == "4321"
    assert "api_key" not in serialized
    assert "encrypted_key" not in serialized
    assert "provider-secret" not in serialized


def test_provider_rejects_unknown_models_before_network_access() -> None:
    with pytest.raises(ProviderFailure) as error:
        GeminiAdapter()._model_id("../private")
    assert error.value.status_code == 422
    assert error.value.code == "unsupported_model"


def test_file_validation_and_text_extraction_are_restricted() -> None:
    assert validate_file("notes.md", "text/markdown", b"# Notes") == ".md"
    assert extract_file_text("notes.md", b"# Notes\n\nUseful text") == "# Notes\nUseful text"
    with pytest.raises(IngestionFailure, match="unsupported_file_type"):
        validate_file("payload.exe", "application/octet-stream", b"bad")
    with pytest.raises(IngestionFailure, match="invalid_pdf"):
        validate_file("notes.pdf", "application/pdf", b"not a pdf")


def test_chunking_preserves_text_and_overlaps() -> None:
    source = "word " * 1000
    chunks = chunk_text(source, size=500, overlap=75)
    assert len(chunks) > 1
    assert all(chunks[index][-40:] in chunks[index + 1] for index in range(len(chunks) - 1))


@pytest.mark.asyncio
async def test_url_dns_guard_rejects_private_addresses(monkeypatch) -> None:
    def private_result(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", private_result)
    with pytest.raises(IngestionFailure, match="url_not_allowed"):
        await _assert_public_host("private.example")


@pytest.mark.asyncio
async def test_url_source_rejects_unusual_ports_before_network_access() -> None:
    with pytest.raises(IngestionFailure, match="url_not_allowed"):
        await fetch_url_text("https://public.example:8443/document")
