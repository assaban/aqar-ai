"""
Aqar.ai - FastAPI Application
=============================
Main application entry point with routes, middleware, and lifespan events.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.core.config import get_settings
from apps.api.app.routers import health, pipeline, properties, search, videos

logger = structlog.get_logger()
settings = get_settings()


# ── Lifespan (startup/shutdown) ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info(
        "Starting Aqar.ai API",
        environment=settings.app_env,
        debug=settings.debug,
    )
    yield
    # Shutdown
    logger.info("Shutting down Aqar.ai API")


# ── Application Factory ──
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Aqar.ai API",
        description=(
            "AI-Driven Real Estate Aggregator — "
            "Extracting structured property data from social media video content."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ──
    app.include_router(health.router, tags=["Health"])
    app.include_router(properties.router, prefix="/api/v1", tags=["Properties"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    app.include_router(videos.router, prefix="/api/v1", tags=["Videos"])
    app.include_router(pipeline.router, prefix="/api/v1", tags=["Pipeline"])

    return app


# ── App Instance ──
app = create_app()
