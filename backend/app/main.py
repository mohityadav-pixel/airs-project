"""AIRS API entrypoint."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import AirsError, airs_error_handler, unhandled_error_handler
from app.core.logging_config import configure_logging, get_logger, log_event
from app.db.init_db import init as init_db

logger = get_logger("airs.api")
limiter = Limiter(key_func=get_remote_address, default_limits=["240/minute"])

DESCRIPTION = """
**AIRS — AI Response & Intervention System.**

Every data-bearing response carries a `provenance` block declaring what kind of
value it is — `observed`, `predicted`, `simulated`, `estimated` or
`ai_generated` — and whether it came from a live provider, cache or the
labelled demo model. Clients are expected to surface that distinction.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    log_event(logger, 20, "airs_started", data_mode=settings.airs_data_mode,
              environment=settings.airs_env)
    yield


app = FastAPI(title="AIRS API", version="1.0.0", description=DESCRIPTION,
              lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(AirsError, airs_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def timing_and_logging(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
    if elapsed_ms > 1500 or response.status_code >= 500:
        log_event(logger, 30, "slow_or_failed_request", path=request.url.path,
                  status=response.status_code, ms=round(elapsed_ms, 1))
    return response


app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "AIRS", "docs": "/docs", "api": "/api/v1"}
