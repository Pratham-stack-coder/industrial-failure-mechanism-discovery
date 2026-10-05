"""
FastAPI Application Entry Point
================================
Industrial Failure Mechanism Discovery System
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging

# Import route modules
from app.api.routes import (
    health,
    datasets,
    investigations,
    mechanisms,
    evaluation,
    data_upload,
)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Create log directory
    os.makedirs("logs", exist_ok=True)
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(settings.experiment_output_dir, exist_ok=True)

    logger.info("Application ready")
    yield
    logger.info("Application shutting down")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-Based Discovery and Ranking of Industrial Failure Mechanisms "
            "from Heterogeneous Temporal Data"
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(datasets.router, prefix="/api/data", tags=["Datasets"])
    app.include_router(data_upload.router, prefix="/api/data", tags=["Upload"])
    app.include_router(investigations.router, prefix="/api/investigations", tags=["Investigations"])
    app.include_router(mechanisms.router, prefix="/api/mechanisms", tags=["Mechanisms"])
    app.include_router(evaluation.router, prefix="/api/evaluation", tags=["Evaluation"])

    return app


app = create_app()
