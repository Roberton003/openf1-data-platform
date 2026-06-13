from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.web.routers import analytics, ci_alerts, telemetry

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

# Include modular routers
app.include_router(telemetry.router)
app.include_router(analytics.router)
app.include_router(ci_alerts.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
