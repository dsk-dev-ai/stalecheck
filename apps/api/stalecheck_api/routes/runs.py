from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..deps import require_api_key
from ..schemas import RunDetail, RunSummary, StatsResponse

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[RunSummary])
async def list_runs(
    request: Request,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_api_key),
) -> list[RunSummary]:
    rows = request.app.state.store.list_runs(limit=limit, offset=offset)
    return [RunSummary(**row) for row in rows]


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    request: Request,
    _: None = Depends(require_api_key),
) -> RunDetail:
    row = request.app.state.store.get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunDetail(**row)


@router.get("/stats", response_model=StatsResponse)
async def stats(
    request: Request,
    _: None = Depends(require_api_key),
) -> StatsResponse:
    return StatsResponse(**request.app.state.store.stats())
