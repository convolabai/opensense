"""Test subscription API with schema validation."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from langhook.app import app
from langhook.subscriptions.llm import NoSuitableSchemaError


@pytest.fixture
def client():
    """Create a test client for the consolidated FastAPI app."""
    with patch('langhook.ingest.nats.nats_producer') as mock_nats, \
         patch('langhook.map.service.mapping_service') as mock_mapping, \
         patch('langhook.ingest.middleware.RateLimitMiddleware.is_rate_limited') as mock_rate_limit, \
         patch('nats.connect') as mock_nats_connect, \
         patch('langhook.subscriptions.database.db_service') as mock_db_service:

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

        # Mock database service
        mock_db_service.create_tables = Mock()

        # Override lifespan for testing by creating a simple mock lifespan
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_lifespan(app):
            yield

        app.router.lifespan_context = mock_lifespan
        with TestClient(app) as client:
            yield client


def test_subscription_creation_with_no_suitable_schema(client):
    """Test subscription creation when no suitable schema is found."""
    with patch('langhook.subscriptions.routes.llm_service.convert_to_pattern') as mock_convert:
        # Mock the LLM service to raise NoSuitableSchemaError
        mock_convert.side_effect = NoSuitableSchemaError("No suitable schema found for description")

        # Try to create a subscription
        subscription_data = {
            "description": "Notify me about Slack messages from channel #general",
            "channel_type": "webhook",
            "channel_config": {
                "url": "http://example.com/webhook",
                "method": "POST"
            }
        }

        response = client.post("/subscriptions/", json=subscription_data)

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert "No suitable event schema found" in error_detail
        assert "Slack messages from channel #general" in error_detail
        assert "/schema endpoint" in error_detail


def test_subscription_update_with_no_suitable_schema(client):
    """Test subscription update when no suitable schema is found."""
    with patch('langhook.subscriptions.routes.llm_service.convert_to_pattern') as mock_convert, \
         patch('langhook.subscriptions.routes.db_service') as mock_db_service:

        # Mock the LLM service to raise NoSuitableSchemaError
        mock_convert.side_effect = NoSuitableSchemaError("No suitable schema found for description")

        # Try to update a subscription description
        update_data = {
            "description": "Notify me about Discord messages"
        }

        response = client.put("/subscriptions/1", json=update_data)

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert "No suitable event schema found" in error_detail
        assert "Discord messages" in error_detail
        assert "/schema endpoint" in error_detail


def test_subscription_creation_with_valid_schema(client):
    """Test subscription creation with valid schema."""
    with patch('langhook.subscriptions.routes.llm_service.convert_to_pattern') as mock_convert, \
         patch('langhook.subscriptions.routes.db_service') as mock_db_service:

        # Mock the LLM service to return a valid pattern
        mock_convert.return_value = "langhook.events.github.pull_request.*.updated"

        # Mock database service to return a subscription
        from unittest.mock import Mock
        mock_subscription = Mock()
        mock_subscription.id = 123
        mock_subscription.description = "GitHub PR updates"
        mock_subscription.channel_type = "webhook"
        mock_subscription.channel_config = {"url": "http://example.com/webhook"}
        mock_subscription.active = True
        mock_subscription.subscriber_id = "default"
        mock_subscription.created_at = "2023-01-01T00:00:00Z"
        mock_subscription.updated_at = "2023-01-01T00:00:00Z"
        mock_subscription.pattern = "langhook.events.github.pull_request.*.updated"

        mock_db_service.create_subscription = AsyncMock(return_value=mock_subscription)

        # Try to create a subscription
        subscription_data = {
            "description": "Notify me about GitHub pull request updates",
            "channel_type": "webhook",
            "channel_config": {
                "url": "http://example.com/webhook",
                "method": "POST"
            }
        }

        response = client.post("/subscriptions/", json=subscription_data)

        # Should succeed
        assert response.status_code == 201
        subscription = response.json()
        assert subscription["id"] == 123
        assert subscription["description"] == "GitHub PR updates"
        assert subscription["pattern"] == "langhook.events.github.pull_request.*.updated"


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
