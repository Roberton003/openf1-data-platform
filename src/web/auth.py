import os
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

API_KEY = os.environ.get("OPENF1_API_KEY", "")

RATE_LIMIT = int(os.environ.get("RATE_LIMIT_REQ_PER_MIN", "100"))
RATE_LIMIT_WINDOW = 60

_rate_store: dict[str, list[float]] = defaultdict(list)


async def verify_api_key(request: Request, call_next):
    if not API_KEY:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    api_key_header = request.headers.get("X-API-Key", "")

    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif api_key_header:
        token = api_key_header

    if request.url.path.startswith(
        (
            "/api/analytics",
            "/api/telemetry",
            "/api/race-intelligence",
            "/api/predictions",
        )
    ):
        if not token or token != API_KEY:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "API key inválida ou ausente. Forneça X-API-Key ou Authorization: Bearer <key>."
                },
            )

    return await call_next(request)


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/api/analytics/query" and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        timestamps = _rate_store[client_ip]
        _rate_store[client_ip] = [t for t in timestamps if t > window_start]

        if len(_rate_store[client_ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Limite de taxa excedido. Máximo de {RATE_LIMIT} requisições por minuto."
                },
            )

        _rate_store[client_ip].append(now)

    return await call_next(request)
