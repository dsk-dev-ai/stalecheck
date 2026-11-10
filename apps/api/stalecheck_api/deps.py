from __future__ import annotations

from fastapi import HTTPException, Request


def require_api_key(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.api_key:
        return
    provided = request.headers.get("x-api-key")
    if provided != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing x-api-key")
