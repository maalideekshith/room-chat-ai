from collections.abc import Sequence
import re
from typing import Protocol

import httpx

from app.core.config import settings
from app.models.solo import EMBEDDING_DIMENSIONS

PROVIDERS = ("openai", "anthropic", "gemini")


class ProviderFailure(Exception):
    def __init__(self, code: str, status_code: int = 502) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class ProviderAdapter(Protocol):
    async def validate(self, api_key: str) -> None: ...
    async def list_models(self, api_key: str) -> list[str]: ...
    async def complete(self, api_key: str, model: str, messages: Sequence[dict[str, str]]) -> str: ...


class EmbeddingAdapter(Protocol):
    async def embed(self, api_key: str, text: str) -> tuple[list[float], str]: ...


class _HttpAdapter:
    provider: str
    transport: httpx.AsyncBaseTransport | None

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    def _headers(self, api_key: str) -> dict[str, str]:
        raise NotImplementedError

    async def _request(
        self, method: str, url: str, api_key: str,
        body: dict | None = None, extra_headers: dict[str, str] | None = None,
    ) -> dict:
        headers = self._headers(api_key)
        headers.update(extra_headers or {})
        try:
            async with httpx.AsyncClient(
                timeout=settings.ai_provider_timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.request(method, url, json=body, headers=headers)
        except httpx.TimeoutException:
            raise ProviderFailure("provider_timeout", 504) from None
        except httpx.HTTPError:
            raise ProviderFailure("provider_unavailable", 502) from None
        if response.status_code == 429:
            raise ProviderFailure("provider_rate_limited", 429)
        if response.status_code in {401, 403}:
            raise ProviderFailure("provider_key_invalid", 422) from None
        if response.status_code >= 500:
            raise ProviderFailure("provider_unavailable", 502) from None
        if response.status_code >= 400:
            raise ProviderFailure("provider_request_rejected", 422) from None
        try:
            data = response.json()
        except ValueError:
            raise ProviderFailure("provider_invalid_response", 502) from None
        if not isinstance(data, dict):
            raise ProviderFailure("provider_invalid_response", 502)
        return data

    async def validate(self, api_key: str) -> None:
        if not await self.list_models(api_key):
            raise ProviderFailure("provider_no_models", 422)

    @staticmethod
    def _model_id(model: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", model):
            raise ProviderFailure("unsupported_model", 422)


class OpenAIAdapter(_HttpAdapter):
    provider = "openai"

    def _headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    async def list_models(self, api_key: str) -> list[str]:
        data = await self._request("GET", "https://api.openai.com/v1/models", api_key)
        values = [item.get("id", "") for item in data.get("data", []) if isinstance(item, dict)]
        not_chat = ("realtime", "audio", "transcribe", "tts", "image", "embedding", "search")
        return sorted(
            model for model in values
            if isinstance(model, str) and model.startswith(("gpt-", "chatgpt-"))
            and not any(part in model for part in not_chat)
        )

    async def complete(self, api_key: str, model: str, messages: Sequence[dict[str, str]]) -> str:
        self._model_id(model)
        instructions = "\n".join(item["content"] for item in messages if item["role"] == "system")
        turns = [item for item in messages if item["role"] != "system"]
        data = await self._request(
            "POST", "https://api.openai.com/v1/responses", api_key,
            {"model": model, "instructions": instructions, "input": turns},
        )
        try:
            answer = "\n".join(
                part["text"] for item in data["output"] for part in item.get("content", [])
                if part.get("type") == "output_text"
            )
        except (KeyError, TypeError):
            raise ProviderFailure("provider_invalid_response", 502) from None
        return _nonempty(answer)

    async def embed(self, api_key: str, text: str) -> tuple[list[float], str]:
        data = await self._request(
            "POST", "https://api.openai.com/v1/embeddings", api_key,
            {"model": "text-embedding-3-small", "input": text, "dimensions": EMBEDDING_DIMENSIONS},
        )
        try:
            vector = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError):
            raise ProviderFailure("provider_invalid_response", 502) from None
        return _vector(vector), "text-embedding-3-small"


class AnthropicAdapter(_HttpAdapter):
    provider = "anthropic"
    version_header = {"anthropic-version": "2023-06-01"}

    def _headers(self, api_key: str) -> dict[str, str]:
        return {"x-api-key": api_key, **self.version_header}

    async def list_models(self, api_key: str) -> list[str]:
        data = await self._request(
            "GET", "https://api.anthropic.com/v1/models", api_key,
        )
        values = [item.get("id", "") for item in data.get("data", []) if isinstance(item, dict)]
        return sorted(model for model in values if isinstance(model, str))

    async def complete(self, api_key: str, model: str, messages: Sequence[dict[str, str]]) -> str:
        self._model_id(model)
        system = "\n".join(item["content"] for item in messages if item["role"] == "system")
        turns = [item for item in messages if item["role"] != "system"]
        data = await self._request(
            "POST", "https://api.anthropic.com/v1/messages", api_key,
            {"model": model, "max_tokens": 2048, "messages": turns, "system": system},
        )
        try:
            answer = "\n".join(item["text"] for item in data["content"] if item["type"] == "text")
        except (KeyError, TypeError):
            raise ProviderFailure("provider_invalid_response", 502) from None
        return _nonempty(answer)


class GeminiAdapter(_HttpAdapter):
    provider = "gemini"

    def _headers(self, api_key: str) -> dict[str, str]:
        return {"x-goog-api-key": api_key}

    async def list_models(self, api_key: str) -> list[str]:
        data = await self._request(
            "GET", "https://generativelanguage.googleapis.com/v1beta/models", api_key,
        )
        values = [
            item for item in data.get("models", [])
            if isinstance(item, dict)
            and "generateContent" in item.get("supportedGenerationMethods", [])
        ]
        return sorted(
            item["name"].removeprefix("models/") for item in values
            if isinstance(item.get("name"), str)
        )

    async def complete(self, api_key: str, model: str, messages: Sequence[dict[str, str]]) -> str:
        self._model_id(model)
        contents = [
            {"role": "model" if item["role"] == "assistant" else "user",
             "parts": [{"text": item["content"]}]}
            for item in messages if item["role"] != "system"
        ]
        system = "\n".join(item["content"] for item in messages if item["role"] == "system")
        data = await self._request(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            api_key,
            {"contents": contents, "systemInstruction": {"parts": [{"text": system}]}},
        )
        try:
            answer = "".join(part["text"] for part in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, TypeError):
            raise ProviderFailure("provider_invalid_response", 502) from None
        return _nonempty(answer)

    async def embed(self, api_key: str, text: str) -> tuple[list[float], str]:
        data = await self._request(
            "POST",
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent",
            api_key,
            {"model": "models/gemini-embedding-001",
             "content": {"parts": [{"text": text}]},
             "outputDimensionality": EMBEDDING_DIMENSIONS},
        )
        try:
            vector = data["embedding"]["values"]
        except (KeyError, TypeError):
            raise ProviderFailure("provider_invalid_response", 502) from None
        return _vector(vector), "gemini-embedding-001"


def _vector(value: object) -> list[float]:
    if not isinstance(value, list) or len(value) != EMBEDDING_DIMENSIONS:
        raise ProviderFailure("embedding_dimension_mismatch", 502)
    if any(not isinstance(item, (float, int)) for item in value):
        raise ProviderFailure("provider_invalid_response", 502)
    return [float(item) for item in value]


def _nonempty(value: str) -> str:
    if not value.strip():
        raise ProviderFailure("provider_empty_response", 502)
    return value.strip()


def adapter_for(provider: str, transport: httpx.AsyncBaseTransport | None = None) -> ProviderAdapter:
    adapters: dict[str, type[_HttpAdapter]] = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "gemini": GeminiAdapter,
    }
    try:
        return adapters[provider](transport)
    except KeyError:
        raise ProviderFailure("unsupported_provider", 422) from None


def embedding_adapter_for(provider: str) -> EmbeddingAdapter:
    adapter = adapter_for(provider)
    if not isinstance(adapter, (OpenAIAdapter, GeminiAdapter)):
        raise ProviderFailure("embedding_provider_required", 422)
    return adapter
