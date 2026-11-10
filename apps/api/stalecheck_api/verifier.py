from __future__ import annotations

from .config import Settings
from .snapshot import SnapshotVerifier
from .tavily import TavilyClient


class Verifier:
    """Snapshot pre-filter, then Tavily for claims the snapshot cannot resolve."""

    def __init__(self, settings: Settings) -> None:
        self.snapshot = SnapshotVerifier()
        self.tavily = TavilyClient(
            settings.tavily_api_key,
            settings.tavily_base_url,
            settings.request_timeout,
        )

    @property
    def live_enabled(self) -> bool:
        return self.tavily.enabled

    async def verify(self, claim: str, use_web: bool = True) -> dict:
        result = self.snapshot.verify(claim)
        if not result.get("needs_judge") or not use_web or not self.tavily.enabled:
            return result

        evidence = await self.tavily.search(f"{claim} current latest", max_results=3)
        if evidence:
            result["evidence"] = evidence
            result["verdict"] = "unverifiable"
            result["confidence"] = 0.45
            result["reason"] = "Live evidence retrieved; awaiting freshness judge."
        else:
            result["needs_judge"] = False
            result["reason"] = "No snapshot match and no live evidence found."
        return result


def get_verifier(settings: Settings) -> Verifier:
    return Verifier(settings)
