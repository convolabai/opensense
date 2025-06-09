"""Test the health endpoint and basic app functionality."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from langhook.app import app


@pytest.fixture
def client():
    """Create a test client for the consolidated FastAPI app."""
    with patch('langhook.ingest.nats.nats_producer') as mock_nats, \
         patch('langhook.map.service.mapping_service') as mock_mapping, \
         patch('langhook.ingest.middleware.RateLimitMiddleware.is_rate_limited') as mock_rate_limit, \
         patch('nats.connect') as mock_nats_connect:
        mock_nats.start = AsyncMock()
        mock_nats.stop = AsyncMock()
        mock_nats.send_raw_event = AsyncMock()
        mock_nats.send_dlq = AsyncMock()

        mock_mapping.run = AsyncMock()

        # Mock rate limiting to always return False (not rate limited)
        mock_rate_limit.return_value = False

        # Mock NATS connection
        from unittest.mock import Mock
        mock_nc = AsyncMock()
        mock_js = Mock()  # JetStream should be sync mock
        mock_js.publish = AsyncMock()
        mock_nc.jetstream = Mock(return_value=mock_js)  # jetstream() should return sync
        mock_nc.close = AsyncMock()
        mock_nats_connect.return_value = mock_nc

        # Override lifespan for testing by creating a simple mock lifespan
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_lifespan(app):
            yield

        app.router.lifespan_context = mock_lifespan
        with TestClient(app) as client:
            yield client


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"
    assert "services" in data
    assert data["services"]["ingest"] == "up"
    assert data["services"]["map"] == "up"


def test_ingest_endpoint_valid_json(client):
    """Test ingesting valid JSON payload."""
    with patch('langhook.ingest.nats.nats_producer') as mock_nats:
        mock_nats.send_raw_event = AsyncMock()

        payload = {"test": "data", "value": 123}
        response = client.post(
            "/ingest/github",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 202
        assert "request_id" in response.json()
        assert response.json()["message"] == "Event accepted"
        assert "X-Request-ID" in response.headers


def test_ingest_endpoint_invalid_json(client):
    """Test ingesting invalid JSON payload."""
    with patch('langhook.ingest.nats.nats_producer') as mock_nats:
        mock_nats.send_dlq = AsyncMock()

        response = client.post(
            "/ingest/github",
            content="invalid json {",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400
        assert "Invalid JSON payload" in response.json()["detail"]


def test_ingest_endpoint_body_too_large(client):
    """Test request body size limit."""
    large_payload = {"data": "x" * 2000000}  # > 1 MiB

    response = client.post(
        "/ingest/test",
        json=large_payload,
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert "Request body too large" in response.json()["detail"]


def test_ingest_endpoint_different_sources(client):
    """Test that different sources are handled correctly."""
    with patch('langhook.ingest.nats.nats_producer') as mock_nats:
        mock_nats.send_raw_event = AsyncMock()

        payload = {"test": "data"}

        # Test GitHub source
        response = client.post("/ingest/github", json=payload)
        assert response.status_code == 202

        # Test Stripe source
        response = client.post("/ingest/stripe", json=payload)
        assert response.status_code == 202

        # Test custom source
        response = client.post("/ingest/custom-app", json=payload)
        assert response.status_code == 202


def test_map_metrics_endpoint(client):
    """Test map metrics endpoint."""
    with patch('langhook.app.mapping_service') as mock_service:
        mock_service.get_metrics.return_value = {
            "events_processed": 100,
            "events_mapped": 95,
            "events_failed": 5,
            "llm_invocations": 3,
            "mapping_success_rate": 0.95,
            "llm_usage_rate": 0.03
        }

        response = client.get("/map/metrics/json")
        assert response.status_code == 200
        data = response.json()
        assert data["events_processed"] == 100
        assert data["events_mapped"] == 95
        assert data["mapping_success_rate"] == 0.95
