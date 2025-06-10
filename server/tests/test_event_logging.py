"""Tests for event logging functionality."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from langhook.subscriptions.event_logging import EventLoggingService, EventLoggingConsumer
from langhook.subscriptions.models import EventLog


@pytest.fixture
def sample_canonical_event():
    """Sample canonical event for testing."""
    return {
        "id": "test-event-123",
        "source": "github",
        "subject": "langhook.events.github.pull_request.456.opened",
        "data": {
            "publisher": "github",
            "resource": {
                "type": "pull_request",
                "id": "456"
            },
            "action": "opened",
            "timestamp": "2023-12-01T12:00:00Z",
            "summary": "Pull request opened",
            "payload": {
                "title": "Add new feature",
                "author": "testuser"
            }
        }
    }


@pytest.fixture
def event_logging_service():
    """Event logging service for testing."""
    return EventLoggingService()


class TestEventLoggingService:
    """Test the EventLoggingService class."""

    @patch('langhook.subscriptions.event_logging.subscription_settings')
    async def test_start_when_disabled(self, mock_settings, event_logging_service):
        """Test that service doesn't start when event logging is disabled."""
        mock_settings.event_logging_enabled = False
        
        await event_logging_service.start()
        
        assert event_logging_service.consumer is None
        assert not event_logging_service._running

    @patch('langhook.subscriptions.event_logging.subscription_settings')
    @patch('langhook.subscriptions.event_logging.db_service')
    async def test_start_when_enabled(self, mock_db_service, mock_settings, event_logging_service):
        """Test that service starts when event logging is enabled."""
        mock_settings.event_logging_enabled = True
        mock_settings.nats_url = "nats://localhost:4222"
        mock_settings.nats_stream_events = "events"
        mock_settings.nats_consumer_group = "test_group"
        mock_db_service.create_event_logs_table.return_value = None
        
        with patch.object(EventLoggingConsumer, 'start', new_callable=AsyncMock) as mock_consumer_start:
            await event_logging_service.start()
            
            mock_db_service.create_event_logs_table.assert_called_once()
            assert event_logging_service.consumer is not None
            mock_consumer_start.assert_called_once()
            assert event_logging_service._running

    @patch('langhook.subscriptions.event_logging.subscription_settings')
    async def test_run_when_disabled(self, mock_settings, event_logging_service):
        """Test that run method exits early when event logging is disabled."""
        mock_settings.event_logging_enabled = False
        
        await event_logging_service.run()
        
        assert event_logging_service.consumer is None

    @patch('langhook.subscriptions.event_logging.db_service')
    async def test_log_event_success(self, mock_db_service, sample_canonical_event, event_logging_service):
        """Test successful event logging."""
        mock_session = MagicMock()
        mock_db_service.get_session.return_value.__enter__.return_value = mock_session
        
        await event_logging_service._log_event(sample_canonical_event)
        
        # Verify session was used
        mock_db_service.get_session.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify EventLog object was created with correct data
        event_log_call = mock_session.add.call_args[0][0]
        assert isinstance(event_log_call, EventLog)
        assert event_log_call.event_id == "test-event-123"
        assert event_log_call.source == "github"
        assert event_log_call.publisher == "github"
        assert event_log_call.resource_type == "pull_request"
        assert event_log_call.resource_id == "456"
        assert event_log_call.action == "opened"

    async def test_log_event_missing_data(self, event_logging_service):
        """Test event logging with missing canonical data."""
        invalid_event = {
            "id": "test-event-123",
            "source": "github",
            "data": {}  # Empty canonical data
        }
        
        # Should not raise an exception, just log a warning
        await event_logging_service._log_event(invalid_event)

    async def test_log_event_missing_required_fields(self, event_logging_service):
        """Test event logging with missing required fields."""
        invalid_event = {
            "id": "test-event-123",
            "source": "github",
            "data": {
                "publisher": "github",
                # Missing resource and action
            }
        }
        
        # Should not raise an exception, just log a warning
        await event_logging_service._log_event(invalid_event)

    @patch('langhook.subscriptions.event_logging.db_service')
    async def test_log_event_database_error(self, mock_db_service, sample_canonical_event, event_logging_service):
        """Test event logging when database error occurs."""
        # Mock database error
        mock_db_service.get_session.side_effect = Exception("Database connection failed")
        
        # Should not raise an exception, just log the error
        await event_logging_service._log_event(sample_canonical_event)


class TestEventLoggingConsumer:
    """Test the EventLoggingConsumer class."""

    @patch('langhook.subscriptions.event_logging.subscription_settings')
    def test_consumer_initialization(self, mock_settings):
        """Test consumer initialization with correct parameters."""
        mock_settings.nats_url = "nats://test:4222"
        mock_settings.nats_stream_events = "test_events"
        mock_settings.nats_consumer_group = "test_group"
        
        handler = AsyncMock()
        consumer = EventLoggingConsumer(handler)
        
        assert consumer.nats_url == "nats://test:4222"
        assert consumer.stream_name == "test_events"
        assert consumer.consumer_name == "test_group_event_logger"
        assert consumer.filter_subject == "langhook.events.>"
        assert consumer.message_handler == handler


@pytest.mark.asyncio
async def test_event_logging_integration():
    """Integration test for event logging with mocked dependencies."""
    
    with patch('langhook.subscriptions.event_logging.subscription_settings') as mock_settings, \
         patch('langhook.subscriptions.event_logging.db_service') as mock_db_service:
        
        # Configure mocks
        mock_settings.event_logging_enabled = True
        mock_settings.nats_url = "nats://localhost:4222"
        mock_settings.nats_stream_events = "events"
        mock_settings.nats_consumer_group = "test_group"
        
        mock_session = MagicMock()
        mock_db_service.get_session.return_value.__enter__.return_value = mock_session
        mock_db_service.create_event_logs_table.return_value = None
        
        # Create service
        service = EventLoggingService()
        
        # Mock the consumer to avoid NATS connection
        with patch.object(EventLoggingConsumer, 'start', new_callable=AsyncMock):
            await service.start()
            
            # Test event logging
            test_event = {
                "id": "integration-test-123",
                "source": "test-source",
                "subject": "langhook.events.test.resource.123.action",
                "data": {
                    "publisher": "test-publisher",
                    "resource": {"type": "test-resource", "id": "123"},
                    "action": "test-action",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"test": "data"}
                }
            }
            
            await service._log_event(test_event)
            
            # Verify event was logged
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify the logged event has correct data
            logged_event = mock_session.add.call_args[0][0]
            assert logged_event.event_id == "integration-test-123"
            assert logged_event.publisher == "test-publisher"
            assert logged_event.resource_type == "test-resource"
            assert logged_event.action == "test-action"


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])