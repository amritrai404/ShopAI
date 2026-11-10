from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import data as data_api

from app.api.analytics import router as analytics_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.forecast import router as forecast_router
from app.core.logging import new_request_id, request_id_var, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ShopAI API",
    description="Your AI Business Partner for small retail shops",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = new_request_id()
    request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"Unhandled error on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal error", "request_id": rid},
        )
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.1f}ms) rid={rid}"
    )
    response.headers["X-Request-ID"] = rid
    return response


app.include_router(analytics_router)
app.include_router(forecast_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(data_api.router, prefix="/data", tags=["Data"])

@app.get("/health")
def health():
    return {"status": "ok", "app": "ShopAI"}