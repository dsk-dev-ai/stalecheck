from __future__ import annotations

import json
import logging
import re
from datetime import date

import httpx

from .config import Settings
from .text import classify_volatility, is_claim_like, split_sentences

log = logging.getLogger("stalecheck.llm")

_PROVIDER_DEFAULTS = {
    "groq": ("https://api.groq.com/openai/v1", "llama-3.1-8b-instant"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.0-flash"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
}


def parse_json(text: str):
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


class RuleBasedLLM:
    """Deterministic extraction + no live judging. Always available, zero cost."""

    provider = "mock"
    supports_live_judge = False

    async def extract_claims(self, text: str, max_claims: int) -> list[dict]:
        seen: set[str] = set()
        claims: list[dict] = []
        for sentence in split_sentences(text):
            if not is_claim_like(sentence):
                continue
            key = sentence.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            _, time_sensitive = classify_volatility(sentence)
            claims.append({"text": sentence, "time_sensitive": time_sensitive})
            if len(claims) >= max_claims:
                break
        if not claims and text.strip():
            claims.append({"text": text.strip()[:400], "time_sensitive": True})
        return claims

    async def judge_claims(self, items: list[dict]) -> list[dict]:
        return [
            {
                "id": item["id"],
                "verdict": "unverifiable",
                "confidence": 0.3,
                "reason": "Live evidence retrieved, but no LLM judge is configured.",
                "suggested_fix": None,
            }
            for item in items
        ]


class OpenAICompatLLM:
    """Works with Groq, Gemini (OpenAI-compatible endpoint), OpenAI or any custom base URL."""

    supports_live_judge = True

    def __init__(self, settings: Settings) -> None:
        provider = settings.llm_provider.lower()
        base, model = _PROVIDER_DEFAULTS.get(provider, (None, None))
        self.provider = provider
        self.base_url = (settings.llm_base_url or base or "").rstrip("/")
        self.model = settings.llm_model or model or ""
        self.api_key = settings.llm_api_key or ""
        self.timeout = settings.request_timeout
        if not self.base_url or not self.model:
            raise ValueError("Custom LLM provider requires LLM_BASE_URL and LLM_MODEL to be set.")

    async def _chat(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def extract_claims(self, text: str, max_claims: int) -> list[dict]:
        system = (
            "You extract atomic, checkable factual claims from AI answers. "
            "Only keep claims that could become outdated: versions, prices, dates, "
            "people, product names, 'latest/current' statements, APIs, policies. "
            'Reply with JSON only: {"claims":[{"text":"...","time_sensitive":true}]}'
        )
        user = f"Max claims: {max_claims}\n\nAnswer:\n{text}"
        try:
            raw = await self._chat(system, user)
            data = parse_json(raw) or {}
            claims = [
                {
                    "text": str(c.get("text", "")).strip(),
                    "time_sensitive": bool(c.get("time_sensitive", True)),
                }
                for c in data.get("claims", [])
                if str(c.get("text", "")).strip()
            ][:max_claims]
            if claims:
                return claims
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM extraction failed, falling back to rules: %s", exc)
        return await RuleBasedLLM().extract_claims(text, max_claims)

    async def judge_claims(self, items: list[dict]) -> list[dict]:
        today = date.today().isoformat()
        system = (
            f"You are a strict freshness judge. Today is {today}. "
            "Use ONLY the supplied evidence. For each claim return fresh, stale or "
            "unverifiable. If stale, provide a corrected statement in suggested_fix. "
            'Reply with JSON only: {"results":[{"id":"...","verdict":"fresh|stale|unverifiable",'
            '"confidence":0.0,"reason":"...","suggested_fix":null}]}'
        )
        compact = [
            {
                "id": item["id"],
                "claim": item["text"],
                "evidence": item.get("evidence", [])[:3],
            }
            for item in items
        ]
        user = json.dumps(compact, ensure_ascii=False)
        try:
            raw = await self._chat(system, user)
            data = parse_json(raw) or {}
            results = data.get("results", []) if isinstance(data, dict) else data
            normalized = []
            for item in results:
                verdict = str(item.get("verdict", "unverifiable")).lower()
                if verdict not in {"fresh", "stale", "unverifiable"}:
                    verdict = "unverifiable"
                normalized.append(
                    {
                        "id": item.get("id"),
                        "verdict": verdict,
                        "confidence": float(item.get("confidence", 0.5)),
                        "reason": str(item.get("reason", "")),
                        "suggested_fix": item.get("suggested_fix"),
                    }
                )
            return normalized
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM judging failed: %s", exc)
            return await RuleBasedLLM().judge_claims(items)


def get_llm(settings: Settings):
    provider = settings.llm_provider.lower()
    if provider == "mock" or not settings.llm_api_key:
        return RuleBasedLLM()
    try:
        return OpenAICompatLLM(settings)
    except ValueError as exc:
        log.warning("Falling back to rule-based LLM: %s", exc)
        return RuleBasedLLM()
