# Room Chat AI - AI Pipeline

## Status

Not implemented. This is the approved target pipeline.

## Provider Abstraction

- One adapter interface for chat completion, embeddings, model listing and credential validation.
- Initial adapters: OpenAI, Anthropic Claude, Google Gemini.
- No global application provider; resolution is per user and per conversation.
- Adapter responses normalize text, usage, finish reason and errors.

## BYOK Resolution

Decided flow for every AI request:
1. Load the conversation and verify access.
2. Resolve provider and credential from conversation settings.
3. Fall back to the user's default provider/model only when the conversation has no explicit selection.
4. Verify the credential belongs to the requesting user and is active.
5. Decrypt the credential in memory.
6. Call the selected provider adapter with the selected model.
7. Record provider, credential ID, model, usage and source references.
8. Discard plaintext key material.

Rules:
- Multiple credentials per provider are supported.
- Users can add, validate, replace and revoke credentials.
- Conversation history survives provider or model changes.
- Credentials are never exposed after saving.
- Other room members never see another user's credential metadata or key.
- API keys never enter logs, traces, errors, analytics or reports.

## Credential Encryption

- Envelope encryption: per-credential data key encrypted by a master key.
- Master key from environment/secret manager, never the database.
- Key version stored for rotation.
- Decryption only server-side, only for the owning user.
- Revocation marks the credential unusable without exposing prior key material.

## Ingestion and Extraction

Planned flow:
1. Receive upload or URL.
2. Validate type, size, ownership and conversation/room authorization.
3. Store immutable source record with checksum.
4. Extract text through an extensible pipeline (PDF, DOCX, TXT, images via OCR).
5. Clean and chunk with overlap.
6. Generate embeddings through the configured embedding provider/model.
7. Store chunks with scope keys plus embedding metadata.
8. Mark source ready or failed.

## Embeddings

- Embedding provider and model are configurable, not fixed to the AI chat provider.
- Every chunk stores `embedding_provider`, `embedding_model`, `embedding_version` and dimensions.
- Model or dimension changes require a re-embedding job.
- Re-embedding respects deleted sources and never resurrects deleted content.
- Retrieval filters by embedding version so mixed-version spaces are not compared.

## Retrieval

- Query is authorized against the active workspace/conversation/room.
- Vector similarity and keyword search combine into ranked context.
- Results are filtered by scope before ranking.
- Context includes source ID, title and locator.
- No cross-room or cross-user retrieval.

## Answering

- System prompt requires grounding and explicit uncertainty.
- Answers include source references.
- Suggestions are separated from confirmed decisions.
- Token and cost usage recorded per AI run.

## Reports

- Scope: Solo workspace or team room.
- Inputs: sources, messages, activity events, confirmed decisions.
- Output sections: overview, completed work, changes, decisions, pending tasks, risks, suggestions.
- Reports store source references and model metadata.
- AI suggestions remain labeled as suggestions.

## OCR and File Types

- Extensible extractor registry by MIME type.
- OCR adapter kept separate from embedding providers.
- Scanned PDFs and images route through OCR.
- Extraction failures are recorded and retryable.

## Open AI Decisions

- Default chunk size and overlap.
- Maximum context and token budget per plan.
- Which OCR provider is used in production.
- Whether room AI may use a member's credential or must use a room-owned credential.
- Whether users may choose embedding models independently of chat models.

## Day 6 Solo implementation

- OpenAI, Anthropic and Gemini chat adapters implement the shared provider protocol; OpenAI and Gemini currently implement the 768-dimensional embedding protocol.
- Provider keys are validated against the provider model endpoint before storage and encrypted with AES-GCM envelope encryption. Set `AI_CREDENTIAL_MASTER_KEY` to base64 for exactly 32 random bytes in the deployment secret manager; do not reuse the JWT secret. Generate a development value with `python -c "import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"`.
- PDF, TXT and Markdown files and public HTTP(S) URLs are ingested synchronously. Extraction errors and provider failures persist a failed source state; chunk rows are inserted only after embedding succeeds.
- Retrieval filters on both source and chunk owner and uses cosine nearest-neighbor ranking. Source text is treated as untrusted prompt context.
- Local files are stored outside the web root behind the `FileStorage` adapter. Production must replace this with private object storage and move ingestion to a durable queue.
