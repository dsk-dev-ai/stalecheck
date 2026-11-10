import httpx
import pytest
from stalecheck_api.config import Settings
from stalecheck_api.llm import OpenAICompatLLM, get_llm


class _Handler:
    def __init__(self, content: str) -> None:
        self.content = content

    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": self.content}},
                ],
            },
        )


def _gemini_llm(monkeypatch, content: str) -> OpenAICompatLLM:
    settings = Settings(
        llm_provider="gemini",
        llm_api_key="test-key",
        llm_model="gemini-2.0-flash",
        llm_base_url="http://mocked.local/v1",
        request_timeout=5.0,
    )
    llm = OpenAICompatLLM(settings)

    real_client = httpx.AsyncClient

    def _patched_client(**kwargs):
        return real_client(
            transport=httpx.MockTransport(_Handler(content)),
            timeout=kwargs.get("timeout", 5.0),
        )

    monkeypatch.setattr(httpx, "AsyncClient", _patched_client)
    return llm


@pytest.mark.asyncio
async def test_openai_compat_extract_claims_uses_chat_completions(monkeypatch):
    llm = _gemini_llm(monkeypatch, '{"claims":[{"text":"GPT-4o is the latest"}]}')
    claims = await llm.extract_claims("GPT-4o is the latest OpenAI model.", max_claims=5)
    assert claims == [{"text": "GPT-4o is the latest", "time_sensitive": True}]


@pytest.mark.asyncio
async def test_openai_compat_judge_parses_results(monkeypatch):
    llm = _gemini_llm(
        monkeypatch, '{"results":[{"id":"c1","verdict":"stale","confidence":0.9,"reason":"old"}]}'
    )
    items = [
        {
            "id": "c1",
            "text": "GPT-4o is the latest OpenAI model.",
            "evidence": [{"title": "Introducing GPT-5", "url": "https://x", "snippet": "y"}],
        }
    ]
    judged = await llm.judge_claims(items)
    assert judged[0]["verdict"] == "stale"
    assert judged[0]["confidence"] == 0.9


def test_openai_compat_llm_supports_gemini():
    settings = Settings(
        llm_provider="gemini",
        llm_api_key="k",
        llm_model="gemini-2.0-flash",
        llm_base_url="http://mocked.local/v1",
    )
    llm = OpenAICompatLLM(settings)
    assert llm.provider == "gemini"
    assert llm.base_url == "http://mocked.local/v1"
    assert llm.model == "gemini-2.0-flash"


def test_get_llm_falls_back_to_rules_when_not_configured():
    settings = Settings(llm_provider="mock", llm_api_key=None)
    assert get_llm(settings).provider == "mock"
