from __future__ import annotations

import logging

import httpx

log = logging.getLogger("stalecheck.tavily")


class TavilyClient:
    """Minimal Tavily search client used for live freshness evidence.

    Free tier is 1,000 searches/month, so the pipeline only calls this for
    claims the offline snapshot cannot resolve.
    """

    def __init__(self, api_key: str | None, base_url: str, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, max_results: int = 3) -> list[dict]:
        if not self.enabled:
            return []
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/search", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - network failures must not break checks
            log.warning("Tavily search failed: %s", exc)
            return []

        evidence = []
        for item in data.get("results", [])[:max_results]:
            evidence.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:600],
                    "published_at": item.get("published_date"),
                }
            )
        return evidence
