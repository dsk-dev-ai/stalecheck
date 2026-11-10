from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .llm import get_llm
from .pipeline import Pipeline
from .routes import check_router, runs_router
from .store import Store
from .verifier import get_verifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("stalecheck")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store = Store(settings.db_path)
    llm = get_llm(settings)
    verifier = get_verifier(settings)

    app.state.settings = settings
    app.state.store = store
    app.state.llm = llm
    app.state.verifier = verifier
    app.state.pipeline = Pipeline(settings, store, llm, verifier)

    log.info(
        "StaleCheck ready provider=%s tavily=%s db=%s",
        llm.provider,
        "on" if verifier.live_enabled else "off",
        settings.db_path,
    )
    try:
        yield
    finally:
        store.close()


app = FastAPI(
    title="StaleCheck API",
    version="1.0.0",
    description="Detect stale, time-sensitive claims in AI answers before users see them.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(check_router, prefix="/v1")
app.include_router(runs_router, prefix="/v1")


@app.get("/")
async def root() -> dict:
    return {
        "name": "StaleCheck API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    verifier = request.app.state.verifier
    return {
        "status": "ok",
        "version": settings.version,
        "provider": llm.provider,
        "live_web": verifier.live_enabled,
        "auth": bool(settings.api_key),
    }
