from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging_config import correlation_id_var, get_correlation_id, setup_logging

logger = structlog.get_logger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID", "")
        if cid:
            correlation_id_var.set(cid)
        else:
            correlation_id_var.set("")
        cid = get_correlation_id()
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings.log_level, settings.log_json)
    logger.info("minova_starting", host=settings.host, port=settings.port)
    yield
    logger.info("minova_shutting_down")


app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Mining Reporting, Verification & Traceability Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    from app.core.database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ready" if db_ok else "degraded",
        "checks": {"database": db_ok},
    }


from sqlalchemy import text

from app.api import entries, reports, approval, conflicts, lineage, documents, chat, anomalies, weather, admin, sync_api


app.include_router(entries.router, prefix=f"{settings.api_prefix}/entries", tags=["Shift Entries"])
app.include_router(reports.router, prefix=f"{settings.api_prefix}/reports", tags=["Reports"])
app.include_router(approval.router, prefix=f"{settings.api_prefix}/approval", tags=["Approval"])
app.include_router(conflicts.router, prefix=f"{settings.api_prefix}/conflicts", tags=["Conflicts"])
app.include_router(lineage.router, prefix=f"{settings.api_prefix}/lineage", tags=["Lineage"])
app.include_router(documents.router, prefix=f"{settings.api_prefix}/documents", tags=["Documents"])
app.include_router(chat.router, prefix=f"{settings.api_prefix}/chat", tags=["AI Chat"])
app.include_router(anomalies.router, prefix=f"{settings.api_prefix}/anomalies", tags=["Anomalies"])
app.include_router(weather.router, prefix=f"{settings.api_prefix}/weather", tags=["Weather"])
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Admin"])
app.include_router(sync_api.router, prefix=f"{settings.api_prefix}/sync", tags=["Sync"])
