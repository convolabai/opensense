"""Test the health endpoint and basic app functionality."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from opensense.ingest.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with patch('opensense.ingest.kafka.kafka_producer') as mock_kafka:
        mock_kafka.start = AsyncMock()
        mock_kafka.stop = AsyncMock()
        mock_kafka.send_event = AsyncMock()
        mock_kafka.send_dlq = AsyncMock()
        
        # Override lifespan for testing
        app.router.lifespan_context = None
        with TestClient(app) as client:
            yield client


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "up"}


def test_ingest_endpoint_valid_json(client):
    """Test ingesting valid JSON payload."""
    with patch('opensense.ingest.kafka.kafka_producer') as mock_kafka:
        mock_kafka.send_event = AsyncMock()
        
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
    with patch('opensense.ingest.kafka.kafka_producer') as mock_kafka:
        mock_kafka.send_dlq = AsyncMock()
        
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
    with patch('opensense.ingest.kafka.kafka_producer') as mock_kafka:
        mock_kafka.send_event = AsyncMock()
        
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