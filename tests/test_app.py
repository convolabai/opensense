"""Test the health endpoint and basic app functionality."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from langhook.app import app


@pytest.fixture
def client():
    """Create a test client for the consolidated FastAPI app."""
    with patch('langhook.ingest.kafka.kafka_producer') as mock_kafka, \
         patch('langhook.map.service.mapping_service') as mock_mapping:
        mock_kafka.start = AsyncMock()
        mock_kafka.stop = AsyncMock()
        mock_kafka.send_event = AsyncMock()
        mock_kafka.send_dlq = AsyncMock()
        
        mock_mapping.run = AsyncMock()
        
        # Override lifespan for testing
        app.router.lifespan_context = None
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
    with patch('langhook.ingest.kafka.kafka_producer') as mock_kafka:
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
    with patch('langhook.ingest.kafka.kafka_producer') as mock_kafka:
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
    with patch('langhook.ingest.kafka.kafka_producer') as mock_kafka:
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


def test_map_metrics_endpoint(client):
    """Test map metrics endpoint."""
    with patch('langhook.map.service.mapping_service') as mock_service:
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