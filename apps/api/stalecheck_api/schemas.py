from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Mode = Literal["annotate", "auto_refresh", "block"]
Verdict = Literal["fresh", "stale", "unverifiable"]
Volatility = Literal["high", "medium", "low"]
Action = Literal["allow", "annotate", "refresh", "block"]


class Evidence(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    published_at: str | None = None


class ClaimResult(BaseModel):
    id: str
    text: str
    volatility: Volatility = "medium"
    time_sensitive: bool = True
    verdict: Verdict = "unverifiable"
    confidence: float = 0.0
    reason: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    suggested_fix: str | None = None


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)
    context: str | None = Field(default=None, max_length=50_000)
    mode: Mode = "annotate"
    use_web: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CheckResponse(BaseModel):
    run_id: str
    verdict: Verdict
    staleness_score: float
    action: Action
    claims: list[ClaimResult]
    mode: Mode
    cached: bool = False
    provider: str = "mock"
    latency_ms: int = 0
    created_at: datetime


class RunSummary(BaseModel):
    run_id: str
    verdict: Verdict
    staleness_score: float
    action: Action
    claims_total: int
    claims_stale: int
    mode: Mode
    provider: str
    preview: str
    created_at: datetime


class RunDetail(CheckResponse):
    input_text: str
    context: str | None = None


class StatsResponse(BaseModel):
    runs: int
    claims: int
    stale_claims: int
    stale_rate: float
    avg_latency_ms: float
