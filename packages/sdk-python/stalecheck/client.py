from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_URL = "http://localhost:8000"


class StaleCheckError(Exception):
    """Raised when the StaleCheck API cannot be reached or returns an error."""


@dataclass
class Evidence:
    title: str = ""
    url: str = ""
    snippet: str = ""
    published_at: str | None = None


@dataclass
class Claim:
    id: str
    text: str
    volatility: str = "medium"
    verdict: str = "unverifiable"
    confidence: float = 0.0
    reason: str = ""
    suggested_fix: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class CheckResult:
    run_id: str
    verdict: str
    staleness_score: float
    action: str
    claims: list[Claim]
    mode: str
    provider: str = "mock"
    cached: bool = False
    latency_ms: int = 0
    created_at: str | None = None

    @property
    def stale_claims(self) -> list[Claim]:
        return [c for c in self.claims if c.verdict == "stale"]

    @property
    def is_stale(self) -> bool:
        return self.verdict == "stale"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "verdict": self.verdict,
            "staleness_score": self.staleness_score,
            "action": self.action,
            "mode": self.mode,
            "provider": self.provider,
            "cached": self.cached,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
            "claims": [
                {
                    "id": c.id,
                    "text": c.text,
                    "volatility": c.volatility,
                    "verdict": c.verdict,
                    "confidence": c.confidence,
                    "reason": c.reason,
                    "suggested_fix": c.suggested_fix,
                    "evidence": [e.__dict__ for e in c.evidence],
                }
                for c in self.claims
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckResult:
        claims = [
            Claim(
                id=str(c.get("id", "")),
                text=str(c.get("text", "")),
                volatility=str(c.get("volatility", "medium")),
                verdict=str(c.get("verdict", "unverifiable")),
                confidence=float(c.get("confidence", 0.0)),
                reason=str(c.get("reason", "")),
                suggested_fix=c.get("suggested_fix"),
                evidence=[Evidence(**e) for e in c.get("evidence", [])],
            )
            for c in data.get("claims", [])
        ]
        return cls(
            run_id=str(data.get("run_id", "")),
            verdict=str(data.get("verdict", "unverifiable")),
            staleness_score=float(data.get("staleness_score", 0.0)),
            action=str(data.get("action", "allow")),
            claims=claims,
            mode=str(data.get("mode", "annotate")),
            provider=str(data.get("provider", "mock")),
            cached=bool(data.get("cached", False)),
            latency_ms=int(data.get("latency_ms", 0)),
            created_at=data.get("created_at"),
        )


class StaleCheck:
    """Client for a StaleCheck API instance."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("STALECHECK_URL") or DEFAULT_URL).rstrip("/")
        self.api_key = api_key or os.getenv("STALECHECK_API_KEY")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}

    def _payload(
        self,
        text: str,
        context: str | None,
        mode: str,
        use_web: bool,
        metadata: dict | None,
    ) -> dict:
        return {
            "text": text,
            "context": context,
            "mode": mode,
            "use_web": use_web,
            "metadata": metadata or {},
        }

    def check(
        self,
        text: str,
        context: str | None = None,
        mode: str = "annotate",
        use_web: bool = True,
        metadata: dict | None = None,
    ) -> CheckResult:
        payload = self._payload(text, context, mode, use_web, metadata)
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=self.timeout, headers=self._headers()
            ) as client:
                resp = client.post("/v1/check", json=payload)
        except httpx.HTTPError as exc:
            raise StaleCheckError(f"Could not reach StaleCheck at {self.base_url}: {exc}") from exc
        if resp.status_code >= 400:
            raise StaleCheckError(f"StaleCheck API error {resp.status_code}: {resp.text[:300]}")
        return CheckResult.from_dict(resp.json())

    async def acheck(
        self,
        text: str,
        context: str | None = None,
        mode: str = "annotate",
        use_web: bool = True,
        metadata: dict | None = None,
    ) -> CheckResult:
        payload = self._payload(text, context, mode, use_web, metadata)
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout, headers=self._headers()
            ) as client:
                resp = await client.post("/v1/check", json=payload)
        except httpx.HTTPError as exc:
            raise StaleCheckError(f"Could not reach StaleCheck at {self.base_url}: {exc}") from exc
        if resp.status_code >= 400:
            raise StaleCheckError(f"StaleCheck API error {resp.status_code}: {resp.text[:300]}")
        return CheckResult.from_dict(resp.json())

    def stats(self) -> dict:
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=self.timeout, headers=self._headers()
            ) as client:
                resp = client.get("/v1/stats")
        except httpx.HTTPError as exc:
            raise StaleCheckError(f"Could not reach StaleCheck at {self.base_url}: {exc}") from exc
        if resp.status_code >= 400:
            raise StaleCheckError(f"StaleCheck API error {resp.status_code}: {resp.text[:300]}")
        return resp.json()
