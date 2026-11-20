from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.encryption import EncryptionUnavailable
from app.ai.providers import ProviderFailure, PROVIDERS
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db_session
from app.models.solo import AiCredential, SoloConversation, SoloMessage, SoloSource
from app.models.user import User
from app.schemas.solo import (
    ConversationCreate,
    ConversationRename,
    ConversationResponse,
    ConversationSettings,
    CredentialCreate,
    CredentialReplace,
    CredentialResponse,
    MessageCreate,
    MessageResponse,
    PreferencesResponse,
    PreferencesUpdate,
    SourceResponse,
    UrlSourceCreate,
)
from app.solo.ingestion import IngestionFailure
from app.solo.service import (
    SoloConfigurationError,
    SoloConflict,
    SoloNotFound,
    create_conversation,
    create_credential,
    create_file_source,
    create_url_source,
    delete_conversation,
    delete_credential,
    delete_source,
    ensure_workspace,
    get_conversation,
    get_messages,
    get_preferences,
    list_conversations,
    list_credentials,
    list_sources,
    rename_conversation,
    replace_credential,
    list_credential_models,
    send_message,
    update_preferences,
    validate_model,
)

router = APIRouter(prefix=f"{settings.api_v1_prefix}/solo", tags=["solo"])


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SoloNotFound):
        return HTTPException(status_code=404, detail="Resource not found")
    if isinstance(exc, SoloConflict):
        return HTTPException(status_code=409, detail="That credential label is already in use")
    if isinstance(exc, EncryptionUnavailable):
        return HTTPException(status_code=503, detail="Credential encryption is not configured")
    if isinstance(exc, SoloConfigurationError):
        if exc.args and exc.args[0] == "credential_encryption_unavailable":
            return HTTPException(status_code=503, detail="Credential encryption is not configured")
        return HTTPException(status_code=503, detail="Credential could not be used securely")
    if isinstance(exc, ProviderFailure):
        messages = {
            "provider_key_invalid": "The provider rejected this API key.",
            "provider_no_models": "This credential did not expose any supported chat models.",
            "provider_rate_limited": "The provider is rate limiting requests. Try again shortly.",
            "provider_timeout": "The provider did not respond in time. Try again.",
            "provider_unavailable": "The provider is temporarily unavailable.",
            "connect_provider_before_chat": "Connect a provider and choose a model before sending a message.",
            "connect_openai_or_gemini_for_knowledge": "Connect an OpenAI or Gemini credential to process knowledge sources.",
            "embedding_provider_required": "This provider does not support knowledge embeddings.",
            "provider_configuration_incomplete": "Choose a provider, credential, and model together.",
            "unsupported_model": "That model is not available for the selected provider.",
        }
        message = messages.get(exc.code, "The provider request could not be completed.")
        return HTTPException(status_code=exc.status_code, detail=message)
    if isinstance(exc, IngestionFailure):
        messages = {
            "unsupported_file_type": "Upload a PDF, text, or Markdown file.",
            "file_too_large": "This file is larger than the upload limit.",
            "invalid_pdf": "The uploaded file is not a valid PDF.",
            "url_not_allowed": "That URL cannot be fetched safely.",
            "url_redirect_not_allowed": "Redirecting URLs are not accepted. Add the final URL directly.",
        }
        code = exc.code
        return HTTPException(status_code=413 if "large" in code else 422,
                             detail=messages.get(code, "The knowledge source could not be processed."))
    return HTTPException(status_code=500, detail="The request could not be completed.")


@router.get("/workspace")
async def workspace(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> dict:
    try:
        row = await ensure_workspace(session, user.id)
        await session.commit()
        return {"id": row.id, "created_at": row.created_at}
    except Exception as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.get("/providers")
async def providers(user: User = Depends(get_current_user)) -> dict:
    del user
    return {"providers": [{"id": provider} for provider in PROVIDERS]}


@router.get("/credentials/{credential_id}/models")
async def credential_models(
    credential_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        return {"models": await list_credential_models(session, user.id, credential_id)}
    except (SoloNotFound, SoloConfigurationError, ProviderFailure) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.get("/conversations", response_model=list[ConversationResponse])
async def conversations(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> list[SoloConversation]:
    return await list_conversations(session, user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SoloConversation:
    try:
        return await get_conversation(session, user.id, conversation_id)
    except SoloNotFound:
        raise _translate_error(SoloNotFound()) from None


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def new_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SoloConversation:
    try:
        return await create_conversation(
            session, user.id, payload.title, payload.provider, payload.credential_id, payload.model
        )
    except (SoloNotFound, SoloConflict, ProviderFailure) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SoloMessage]:
    try:
        return await get_messages(session, user.id, conversation_id)
    except SoloNotFound:
        raise _translate_error(SoloNotFound()) from None


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse], status_code=201,
)
async def send(
    conversation_id: UUID,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SoloMessage]:
    try:
        user_message, assistant_message = await send_message(
            session, user.id, conversation_id, payload.content
        )
        return [user_message, assistant_message]
    except (SoloNotFound, SoloConfigurationError, ProviderFailure) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def rename(
    conversation_id: UUID,
    payload: ConversationRename,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SoloConversation:
    try:
        return await rename_conversation(session, user.id, conversation_id, payload.title)
    except SoloNotFound:
        raise _translate_error(SoloNotFound()) from None


@router.put("/conversations/{conversation_id}/ai-settings", response_model=ConversationResponse)
async def conversation_settings(
    conversation_id: UUID,
    payload: ConversationSettings,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SoloConversation:
    try:
        conversation = await get_conversation(session, user.id, conversation_id)
        if (payload.provider is None) != (payload.credential_id is None) or (
            payload.provider is None
        ) != (payload.model is None):
            raise ProviderFailure("provider_configuration_incomplete", 422)
        if payload.provider:
            await validate_model(
                session, user.id, payload.credential_id, payload.provider, payload.model
            )
        conversation.ai_provider = payload.provider
        conversation.ai_credential_id = payload.credential_id
        conversation.ai_model = payload.model
        await session.commit()
        await session.refresh(conversation)
        return conversation
    except (SoloNotFound, SoloConfigurationError, ProviderFailure) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await delete_conversation(session, user.id, conversation_id)
    except SoloNotFound:
        raise _translate_error(SoloNotFound()) from None


@router.get("/credentials", response_model=list[CredentialResponse])
async def credentials(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> list[AiCredential]:
    return await list_credentials(session, user.id)


@router.post("/credentials", response_model=CredentialResponse, status_code=201)
async def add_credential(
    payload: CredentialCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AiCredential:
    try:
        return await create_credential(
            session, user.id, payload.provider, payload.label, payload.api_key.get_secret_value()
        )
    except (ProviderFailure, SoloConfigurationError, SoloConflict, EncryptionUnavailable) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.patch("/credentials/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: UUID,
    payload: CredentialReplace,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AiCredential:
    try:
        return await replace_credential(
            session, user.id, credential_id,
            label=payload.label,
            api_key=payload.api_key.get_secret_value() if payload.api_key else None,
        )
    except (SoloNotFound, ProviderFailure, SoloConfigurationError, EncryptionUnavailable) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_credential(
    credential_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await delete_credential(session, user.id, credential_id)
    except SoloNotFound:
        raise _translate_error(SoloNotFound()) from None


@router.get("/preferences", response_model=PreferencesResponse)
async def preferences(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> dict:
    row = await get_preferences(session, user.id)
    return {"provider": row.default_provider if row else None,
            "credential_id": row.default_credential_id if row else None,
            "model": row.default_model if row else None}


@router.put("/preferences", response_model=PreferencesResponse)
async def set_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        row = await update_preferences(
            session, user.id, payload.provider, payload.credential_id, payload.model
        )
        return {"provider": row.default_provider, "credential_id": row.default_credential_id,
                "model": row.default_model}
    except (SoloNotFound, ProviderFailure) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.get("/sources", response_model=list[SourceResponse])
async def sources(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> list[SoloSource]:
    return await list_sources(session, user.id)


@router.post("/sources/files", response_model=SourceResponse, status_code=201)
async def upload_source(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SoloSource:
    data = await file.read(settings.solo_max_upload_bytes + 1)
    try:
        return await create_file_source(
            session, user.id, file.filename or "upload", file.content_type, data
        )
    except (IngestionFailure, SoloConfigurationError, ProviderFailure, EncryptionUnavailable) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.post("/sources/urls", response_model=SourceResponse, status_code=201)
async def add_url_source(
    payload: UrlSourceCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SoloSource:
    try:
        return await create_url_source(session, user.id, str(payload.url))
    except (SoloConfigurationError, ProviderFailure, EncryptionUnavailable) as exc:
        await session.rollback()
        raise _translate_error(exc) from None


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_source(
    source_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await delete_source(session, user.id, source_id)
    except SoloNotFound:
        raise _translate_error(SoloNotFound()) from None
