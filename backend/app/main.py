from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, alerts, analytics, assistant, auth, cases, graph, models, simulation, transactions, users, websocket
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await init_db()
    yield


app = FastAPI(
    title="FraudMesh XAI API",
    description="Explainable temporal graph intelligence for coordinated fraud investigations.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
for router in [auth.router, users.router, transactions.router, alerts.router, graph.router, cases.router, analytics.router, models.router, assistant.router, simulation.router, websocket.router, admin.router]:
    app.include_router(router, prefix=api_prefix)


@app.get("/health")
async def health() -> dict:
    return {"status": "operational", "service": "fraudmesh-api", "environment": settings.environment, "simulation": "available" if settings.simulation_enabled else "disabled"}
