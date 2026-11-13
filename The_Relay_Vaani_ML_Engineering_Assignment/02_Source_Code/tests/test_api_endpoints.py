import pytest
import httpx
from src.api.main import app

@pytest.mark.asyncio
async def test_api_health():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "ok")
        assert "groq_configured" in data

@pytest.mark.asyncio
async def test_api_metrics():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_concurrency" in data
        assert "queue_length" in data
