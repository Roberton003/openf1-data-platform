# ---------------------------------------------------------------------------
# Structured Logging bootstrap
# ---------------------------------------------------------------------------
# Set OPENF1_LOG_LEVEL to DEBUG/INFO/etc. to control verbosity.
# Set OPENF1_JSON_LOGS=false to disable JSON formatting (useful for dev).
import os as _os
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.web.auth import rate_limit_middleware, verify_api_key
from src.web.database import close_shared_connection
from src.web.health import router as health_router
from src.web.logging import configure_logging, generate_request_id, get_request_logger
from src.web.routers import analytics, ci_alerts, race_intelligence, telemetry

_log_level = _os.environ.get("OPENF1_LOG_LEVEL", "INFO")
_json_logs = _os.environ.get("OPENF1_JSON_LOGS", "true").lower() != "false"
configure_logging(level=_log_level, json_format=_json_logs)
logger = get_request_logger("openf1.main")

# ---------------------------------------------------------------------------
# Request ID context variable (accessible from handlers for log correlation)
# ---------------------------------------------------------------------------
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    logger.info("openf1_api_startup", extra={"version": application.version})
    yield
    close_shared_connection()
    logger.info("openf1_api_shutdown")


app = FastAPI(
    title="OpenF1 Telemetry Dashboard API",
    description="Backend API and web engine for F1 analytics local data platform",
    version="1.1.0",  # Bumped for health endpoints + hardened SQL Gateway
    lifespan=lifespan,
)

# CORS middleware config — restricted via env var
_cors_origins = _os.environ.get(
    "CORS_ORIGINS", "http://localhost:8001,http://localhost:8501"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware stack: Request ID → Timing → Logging
# (FastAPI middlewares execute in reverse order of definition)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for log correlation."""
    # Allow client to pass a request ID via header for distributed tracing.
    req_id = request.headers.get("X-Request-ID") or generate_request_id()
    _request_id_var.set(req_id)

    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with method, path, status, and duration."""
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "request_id": _request_id_var.get(),
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", "")[:200],
            },
        )
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            "request_failed",
            extra={
                "request_id": _request_id_var.get(),
                "method": request.method,
                "endpoint": request.url.path,
                "duration_ms": duration_ms,
                "error": str(exc)[:500],
            },
        )
        raise


# ---------------------------------------------------------------------------
# Auth middleware (API key validation)
# ---------------------------------------------------------------------------
app.middleware("http")(verify_api_key)

# ---------------------------------------------------------------------------
# Rate limiting middleware (SQL gateway)
# ---------------------------------------------------------------------------
app.middleware("http")(rate_limit_middleware)

# ---------------------------------------------------------------------------
# Include modular routers
# ---------------------------------------------------------------------------
app.include_router(telemetry.router)
app.include_router(analytics.router)
app.include_router(race_intelligence.router)
app.include_router(ci_alerts.router)
app.include_router(health_router)

# ---------------------------------------------------------------------------
# Static files and root route
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).resolve().parent / "static"
RACE_INTELLIGENCE_INDEX = STATIC_DIR / "race_intelligence" / "index.html"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def race_intelligence_home():
    return FileResponse(RACE_INTELLIGENCE_INDEX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
