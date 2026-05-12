"""
Unit tests for the health check endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_ok():
    """GET /health should return status ok."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_contains_environment():
    """GET /health should include environment info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    data = response.json()
    assert "environment" in data
