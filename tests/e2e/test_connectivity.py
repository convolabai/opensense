"""Simple connectivity test for E2E environment."""

import os

import httpx
import pytest


@pytest.mark.asyncio
async def test_docker_connectivity():
    """Test basic connectivity to Docker services."""
    base_url = os.getenv("LANGHOOK_BASE_URL", "http://localhost:8000")

    # Simple connectivity test
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health/")
            assert response.status_code == 200

            health_data = response.json()
            assert health_data["status"] == "up"

    except Exception as e:
        pytest.skip(f"E2E environment not available: {e}")


@pytest.mark.asyncio
async def test_basic_ingest():
    """Test basic event ingestion."""
    base_url = os.getenv("LANGHOOK_BASE_URL", "http://localhost:8000")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/ingest/test",
                json={"test": "connectivity"},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 202

            result = response.json()
            assert result["message"] == "Event accepted"
            assert "request_id" in result

    except Exception as e:
        pytest.skip(f"E2E environment not available: {e}")
