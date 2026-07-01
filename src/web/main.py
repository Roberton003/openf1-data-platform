from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.web.database import close_shared_connection
from src.web.routers import ci_alerts, sla


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield
    close_shared_connection()


app = FastAPI(
    title="OpenF1 Web API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sla.router)
app.include_router(ci_alerts.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
