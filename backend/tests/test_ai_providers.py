import json

import httpx
import pytest

from app.ai.providers import AnthropicAdapter, GeminiAdapter, OpenAIAdapter, ProviderFailure


@pytest.mark.asyncio
async def test_openai_adapter_sends_messages_and_normalizes_completion() -> None:
    captured: list[httpx.Request] = []

    def response(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"output": [{"content": [{"type": "output_text", "text": "A grounded answer."}]}]})

    adapter = OpenAIAdapter(httpx.MockTransport(response))
    answer = await adapter.complete(
        "provider-secret",
        "gpt-4.1-mini",
        [{"role": "user", "content": "Question"}],
    )
    assert answer == "A grounded answer."
    assert captured[0].url.path == "/v1/responses"
    assert captured[0].headers["Authorization"] == "Bearer provider-secret"
    assert json.loads(captured[0].content)["input"][0]["content"] == "Question"


@pytest.mark.asyncio
async def test_provider_errors_are_normalized_without_returning_provider_body() -> None:
    captured: list[httpx.Request] = []
    def unauthorized(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(401, json={"error": "provider-secret"})
    adapter = AnthropicAdapter(httpx.MockTransport(unauthorized))
    with pytest.raises(ProviderFailure) as error:
        await adapter.validate("provider-secret")
    assert error.value.code == "provider_key_invalid"
    assert "provider-secret" not in str(error.value)
    assert captured[0].headers["x-api-key"] == "provider-secret"


@pytest.mark.asyncio
async def test_gemini_model_list_is_filtered_to_generate_content_support() -> None:
    adapter = GeminiAdapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json={
            "models": [
                {"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
            ],
        })),
    )
    assert await adapter.list_models("secret") == ["gemini-3.8-flash"]
