import pytest
from httpx import AsyncClient
from apps.api.app.main import app

@pytest.mark.asyncio
async def test_api_is_running():
    """Verify the API is reachable for integration tests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200