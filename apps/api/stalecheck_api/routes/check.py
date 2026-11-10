from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..deps import require_api_key
from ..schemas import CheckRequest, CheckResponse

router = APIRouter(tags=["check"])


@router.post("/check", response_model=CheckResponse)
async def check(
    payload: CheckRequest,
    request: Request,
    _: None = Depends(require_api_key),
) -> CheckResponse:
    return await request.app.state.pipeline.check(payload)
