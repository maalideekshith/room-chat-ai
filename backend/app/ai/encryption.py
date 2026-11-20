import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class EncryptionUnavailable(Exception):
    pass


def _master_key() -> bytes:
    configured = settings.ai_credential_master_key
    if not configured:
        raise EncryptionUnavailable
    try:
        key = base64.b64decode(configured, validate=True)
    except (ValueError, TypeError):
        raise EncryptionUnavailable from None
    if len(key) != 32:
        raise EncryptionUnavailable
    return key


def encrypt_api_key(api_key: str) -> tuple[bytes, bytes]:
    master = AESGCM(_master_key())
    dek = AESGCM.generate_key(bit_length=256)
    dek_nonce = secrets.token_bytes(12)
    key_nonce = secrets.token_bytes(12)
    encrypted_dek = dek_nonce + master.encrypt(dek_nonce, dek, b"room-chat-ai:dek:v1")
    encrypted_key = key_nonce + AESGCM(dek).encrypt(
        key_nonce, api_key.encode("utf-8"), b"room-chat-ai:provider-key:v1"
    )
    return encrypted_dek, encrypted_key


def decrypt_api_key(encrypted_dek: bytes, encrypted_key: bytes) -> str:
    master = AESGCM(_master_key())
    dek = master.decrypt(encrypted_dek[:12], encrypted_dek[12:], b"room-chat-ai:dek:v1")
    cleartext = AESGCM(dek).decrypt(
        encrypted_key[:12], encrypted_key[12:], b"room-chat-ai:provider-key:v1"
    )
    return cleartext.decode("utf-8")
