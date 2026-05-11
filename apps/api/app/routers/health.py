"""
Aqar.ai - Health Check Routes
=============================
Liveness and readiness probes for monitoring and orchestration.
"""

import redis.asyncio as redis
import structlog
from fastapi import APIRouter

from apps.api.app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic liveness probe.
    Returns 200 if the API process is running.
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app_env,
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe - checks all dependencies.
    Used by orchestrators to determine if the service can accept traffic.
    """
    services = {}

    # Check PostgreSQL
    try:
        from apps.api.app.core.database import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "ok"
    except Exception as e:
        services["postgres"] = f"error: {e}"
        logger.error("PostgreSQL health check failed", error=str(e))

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        services["redis"] = "ok"
    except Exception as e:
        services["redis"] = f"error: {e}"
        logger.error("Redis health check failed", error=str(e))

    # Check Meilisearch
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.meilisearch_url}/health", timeout=5.0)
            services["meilisearch"] = "ok" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as e:
        services["meilisearch"] = f"error: {e}"
        logger.error("Meilisearch health check failed", error=str(e))

    all_ok = all(v == "ok" for v in services.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "version": "0.1.0",
        "services": services,
    }
