import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.web.routers import analytics, ci_alerts, observabilidade, pages, telemetry

app = FastAPI(
    title="OpenF1 Telemetry Dashboard API",
    description="Backend API and web engine for F1 analytics local data platform",
    version="1.0.0",
)

# CORS middleware config to allow cross-origin client queries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set path for static assets
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

# Ensure static directories exist
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include modular routers
app.include_router(pages.router)
app.include_router(telemetry.router)
app.include_router(analytics.router)
app.include_router(observabilidade.router)
app.include_router(ci_alerts.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
