from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime

from .config import Settings
from .schemas import CheckRequest, CheckResponse, ClaimResult, Evidence
from .store import Store
from .text import classify_volatility


class Pipeline:
    def __init__(self, settings: Settings, store: Store, llm, verifier) -> None:
        self.settings = settings
        self.store = store
        self.llm = llm
        self.verifier = verifier

    def _cache_key(self, req: CheckRequest) -> str:
        raw = json.dumps(
            {
                "text": req.text,
                "context": req.context,
                "mode": req.mode,
                "use_web": req.use_web,
                "provider": self.llm.provider,
            },
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def check(self, req: CheckRequest) -> CheckResponse:
        started = time.perf_counter()
        key = self._cache_key(req)

        cached = self.store.get_cache(key)
        if cached is not None:
            cached["cached"] = True
            return CheckResponse(**cached)

        raw_claims = await self.llm.extract_claims(req.text, self.settings.max_claims)
        claims: list[ClaimResult] = []
        for index, item in enumerate(raw_claims[: self.settings.max_claims]):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            volatility, time_sensitive = classify_volatility(text)
            claims.append(
                ClaimResult(
                    id=f"c{index + 1}",
                    text=text,
                    volatility=volatility,  # type: ignore[arg-type]
                    time_sensitive=bool(item.get("time_sensitive", time_sensitive)),
                    verdict="unverifiable",
                    reason="Not checked.",
                )
            )

        targets = [c for c in claims if c.volatility != "low"][: self.settings.max_judged_claims]
        semaphore = asyncio.Semaphore(3)

        async def verify(claim: ClaimResult) -> dict:
            async with semaphore:
                return await self.verifier.verify(claim.text, req.use_web)

        results = await asyncio.gather(*(verify(c) for c in targets)) if targets else []

        needs_judge: list[dict] = []
        for claim, result in zip(targets, results, strict=False):
            self._apply(claim, result)
            if result.get("needs_judge") and self.llm.supports_live_judge:
                needs_judge.append(
                    {"id": claim.id, "text": claim.text, "evidence": result.get("evidence", [])}
                )

        if needs_judge:
            judged = await self.llm.judge_claims(needs_judge)
            by_id = {str(item.get("id")): item for item in judged}
            for claim in claims:
                verdict = by_id.get(claim.id)
                if verdict:
                    claim.verdict = verdict.get("verdict", "unverifiable")  # type: ignore[assignment]
                    claim.confidence = float(verdict.get("confidence", claim.confidence))
                    claim.reason = str(verdict.get("reason") or claim.reason)
                    claim.suggested_fix = verdict.get("suggested_fix") or claim.suggested_fix

        for claim in claims:
            if claim in targets:
                continue
            claim.verdict = "fresh" if claim.volatility == "low" else "unverifiable"
            claim.confidence = 0.5
            claim.reason = (
                "Stable claim; nothing time-sensitive to check."
                if claim.volatility == "low"
                else "Not checked (claim budget reached)."
            )

        stale = [c for c in claims if c.verdict == "stale"]
        fresh = [c for c in claims if c.verdict == "fresh"]
        if stale:
            verdict = "stale"
        elif claims and len(fresh) == len(claims):
            verdict = "fresh"
        else:
            verdict = "unverifiable"

        score = (len(stale) / len(claims)) if claims else 0.0
        action = self._action(verdict, req.mode)

        latency_ms = int((time.perf_counter() - started) * 1000)
        response = CheckResponse(
            run_id=f"sc_{uuid.uuid4().hex[:16]}",
            verdict=verdict,  # type: ignore[arg-type]
            staleness_score=round(score, 4),
            action=action,
            claims=claims,
            mode=req.mode,
            cached=False,
            provider=self.llm.provider,
            latency_ms=latency_ms,
            created_at=datetime.now(UTC),
        )

        payload = response.model_dump(mode="json")
        self.store.save_run({**payload, "input_text": req.text, "context": req.context})
        self.store.set_cache(key, payload, self.settings.cache_ttl_seconds)
        return response

    def _apply(self, claim: ClaimResult, result: dict) -> None:
        verdict = result.get("verdict", "unverifiable")
        if verdict not in {"fresh", "stale", "unverifiable"}:
            verdict = "unverifiable"
        claim.verdict = verdict  # type: ignore[assignment]
        claim.confidence = float(result.get("confidence", 0.0))
        claim.reason = str(result.get("reason", ""))
        claim.suggested_fix = result.get("suggested_fix")
        claim.evidence = [
            Evidence(**item) for item in result.get("evidence", []) if isinstance(item, dict)
        ]

    @staticmethod
    def _action(verdict: str, mode: str) -> str:
        if verdict != "stale":
            return "allow"
        if mode == "block":
            return "block"
        if mode == "auto_refresh":
            return "refresh"
        return "annotate"
