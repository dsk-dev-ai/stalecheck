from __future__ import annotations

import json
import re
from pathlib import Path

from .text import alias_in_text, normalize

DEFAULT_SNAPSHOT = Path(__file__).parent / "data" / "snapshot.json"

_MARKER = re.compile(
    r"\b(?:latest|current|currently|newest|now|flagship|state of the art|lts)\b",
    re.IGNORECASE,
)
_NEGATED_MARKER = re.compile(
    r"\b(?:not|no longer|isn't|aren't|isnt|arent)\s+the\s+(?:latest|current|newest)\b",
    re.IGNORECASE,
)


class SnapshotVerifier:
    """Offline freshness check against a bundled, dated knowledge snapshot.

    This is deliberately cheap and deterministic: it powers the demo/mock mode
    and acts as a pre-filter before spending a Tavily search credit.
    """

    provider = "snapshot"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_SNAPSHOT
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.as_of = self.data.get("as_of", "")
        self.facts = self.data.get("facts", [])

    def verify(self, claim: str) -> dict:
        text = normalize(claim)

        for fact in self.facts:
            if any(normalize(p) in text for p in fact.get("stale_phrases", [])):
                return self._result(
                    "stale",
                    0.92,
                    f"Contradicts a dated fact (snapshot as of {self.as_of}).",
                    fact,
                    suggested_fix=fact.get("current"),
                )

        has_marker = bool(_MARKER.search(text))
        negated = bool(_NEGATED_MARKER.search(text))
        if has_marker:
            for fact in self.facts:
                outdated = any(alias_in_text(a, text) for a in fact.get("outdated_aliases", []))
                current = any(alias_in_text(a, text) for a in fact.get("current_aliases", []))
                if outdated and not negated:
                    return self._result(
                        "stale",
                        0.8,
                        "Mentions a superseded value as current/latest.",
                        fact,
                        suggested_fix=fact.get("current"),
                    )
                if outdated and negated:
                    return self._result(
                        "fresh",
                        0.72,
                        "Correctly states that the superseded value is no longer current.",
                        fact,
                    )
                if current and not negated:
                    return self._result(
                        "fresh",
                        0.8,
                        "Mentions the current value as current/latest.",
                        fact,
                    )
                if current and negated:
                    return self._result(
                        "stale",
                        0.72,
                        "Denies the current value; the snapshot says otherwise.",
                        fact,
                        suggested_fix=fact.get("current"),
                    )

        for fact in self.facts:
            if any(normalize(p) in text for p in fact.get("fresh_phrases", [])):
                return self._result(
                    "fresh",
                    0.88,
                    f"Matches the current value in the snapshot (as of {self.as_of}).",
                    fact,
                )

        for fact in self.facts:
            if any(alias_in_text(a, text) for a in fact.get("aliases", [])):
                return self._result(
                    "unverifiable",
                    0.45,
                    "Known topic, but the claim is not specific enough to confirm freshness.",
                    fact,
                    suggested_fix=fact.get("current"),
                )

        return {
            "verdict": "unverifiable",
            "confidence": 0.2,
            "reason": "No freshness source covers this claim yet.",
            "evidence": [],
            "suggested_fix": None,
            "needs_judge": True,
            "topic": None,
        }

    def _result(
        self,
        verdict: str,
        confidence: float,
        reason: str,
        fact: dict,
        suggested_fix: str | None = None,
    ) -> dict:
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reason": reason,
            "evidence": [
                {
                    "title": fact.get("source_title", fact.get("topic", "")),
                    "url": fact.get("source_url", ""),
                    "snippet": fact.get("current", ""),
                    "published_at": self.as_of,
                }
            ],
            "suggested_fix": suggested_fix,
            "needs_judge": False,
            "topic": fact.get("topic"),
        }
