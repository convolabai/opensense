"""Test optional webhook functionality in subscription API."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from langhook.app import app


@pytest.fixture
def client():
    """Create a test client for the consolidated FastAPI app."""
    with patch("langhook.core.nats.nats.connect") as mock_nats_connect:
        # Mock NATS connection for testing
        mock_nc = Mock()
        mock_js = Mock()
        mock_js.add_stream = AsyncMock()
        mock_js.add_consumer = AsyncMock()
        mock_nc.jetstream = Mock(return_value=mock_js)  # jetstream() should return sync
        mock_nc.close = AsyncMock()
        mock_nats_connect.return_value = mock_nc

        # Mock database service
        with patch("langhook.subscriptions.routes.db_service") as mock_db_service:
            mock_db_service.create_tables = Mock()

            # Mock the consumer service
            with patch("langhook.subscriptions.routes.get_consumer_service") as mock_get_consumer_service:
                mock_consumer_service = Mock()
                mock_consumer_service.add_subscription = AsyncMock()
                mock_consumer_service.remove_subscription = AsyncMock()
                mock_consumer_service.update_subscription = AsyncMock()
                mock_get_consumer_service.return_value = mock_consumer_service

                # Override lifespan for testing by creating a simple mock lifespan
                from contextlib import asynccontextmanager

                @asynccontextmanager
                async def mock_lifespan(app):
                    yield

                app.router.lifespan_context = mock_lifespan
                with TestClient(app) as client:
                    yield client, mock_db_service


def test_subscription_creation_without_webhook(client):
    """Test subscription creation without webhook (polling-only)."""
    test_client, mock_db_service = client
    
    with patch('langhook.subscriptions.routes.llm_service.convert_to_pattern') as mock_convert:
        # Mock the LLM service to return a pattern
        mock_convert.return_value = "langhook.events.github.pull_request.*.opened"

        # Mock the database service
        mock_subscription = Mock()
        mock_subscription.id = 123
        mock_subscription.subscriber_id = "default"
        mock_subscription.description = "GitHub PR opened"
        mock_subscription.pattern = "langhook.events.github.pull_request.*.opened"
        mock_subscription.channel_type = None
        mock_subscription.channel_config = None
        mock_subscription.active = True
        mock_subscription.created_at = "2023-01-01T00:00:00Z"
        mock_subscription.updated_at = None

        mock_db_service.create_subscription = AsyncMock(return_value=mock_subscription)

        # Try to create a subscription without webhook
        subscription_data = {
            "description": "Notify me about GitHub pull request opens"
        }

        response = test_client.post("/subscriptions/", json=subscription_data)

        # Should succeed
        assert response.status_code == 201
        subscription = response.json()
        assert subscription["id"] == 123
        assert subscription["description"] == "GitHub PR opened"
        assert subscription["pattern"] == "langhook.events.github.pull_request.*.opened"
        assert subscription["channel_type"] is None
        assert subscription["channel_config"] is None

        # Verify database service was called with correct parameters
        mock_db_service.create_subscription.assert_called_once()
        call_args = mock_db_service.create_subscription.call_args
        subscription_data_arg = call_args[1]["subscription_data"]
        assert subscription_data_arg.description == "Notify me about GitHub pull request opens"
        assert subscription_data_arg.channel_type is None
        assert subscription_data_arg.channel_config is None


def test_subscription_creation_with_webhook(client):
    """Test subscription creation with webhook still works."""
    test_client, mock_db_service = client
    
    with patch('langhook.subscriptions.routes.llm_service.convert_to_pattern') as mock_convert:
        # Mock the LLM service to return a pattern
        mock_convert.return_value = "langhook.events.github.pull_request.*.opened"

        # Mock the database service
        mock_subscription = Mock()
        mock_subscription.id = 124
        mock_subscription.subscriber_id = "default"
        mock_subscription.description = "GitHub PR opened"
        mock_subscription.pattern = "langhook.events.github.pull_request.*.opened"
        mock_subscription.channel_type = "webhook"
        mock_subscription.channel_config = {"url": "http://example.com/webhook", "method": "POST"}
        mock_subscription.active = True
        mock_subscription.created_at = "2023-01-01T00:00:00Z"
        mock_subscription.updated_at = None

        mock_db_service.create_subscription = AsyncMock(return_value=mock_subscription)

        # Try to create a subscription with webhook
        subscription_data = {
            "description": "Notify me about GitHub pull request opens",
            "channel_type": "webhook",
            "channel_config": {
                "url": "http://example.com/webhook",
                "method": "POST"
            }
        }

        response = test_client.post("/subscriptions/", json=subscription_data)

        # Should succeed
        assert response.status_code == 201
        subscription = response.json()
        assert subscription["id"] == 124
        assert subscription["description"] == "GitHub PR opened"
        assert subscription["pattern"] == "langhook.events.github.pull_request.*.opened"
        assert subscription["channel_type"] == "webhook"


def test_event_logs_endpoint_exists(client):
    """Test that /event-logs endpoint exists and works."""
    test_client, mock_db_service = client
    
    # Mock the get_event_logs method
    mock_event_logs = []
    
    with patch("langhook.subscriptions.database.db_service") as mock_app_db_service:
        mock_app_db_service.get_event_logs = AsyncMock(return_value=(mock_event_logs, 0))

        response = test_client.get("/event-logs")

        # Should succeed
        assert response.status_code == 200
        data = response.json()
        assert "event_logs" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["event_logs"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 50


def test_subscription_events_endpoint_exists(client):
    """Test that /subscriptions/{id}/events endpoint exists and works."""
    test_client, mock_db_service = client
    
    # Mock getting a subscription
    mock_subscription = Mock()
    mock_subscription.id = 123
    mock_subscription.pattern = "langhook.events.github.pull_request.*.opened"
    mock_db_service.get_subscription = AsyncMock(return_value=mock_subscription)
    
    # Mock the get_subscription_events method (now returns SubscriptionEventLog objects)
    mock_subscription_events = []
    mock_db_service.get_subscription_events = AsyncMock(return_value=(mock_subscription_events, 0))

    response = test_client.get("/subscriptions/123/events")

    # Should succeed
    assert response.status_code == 200
    data = response.json()
    assert "event_logs" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert data["event_logs"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 50


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])