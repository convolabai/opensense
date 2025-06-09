"""End-to-end test for event logging with enabled configuration."""

import pytest
import os
from unittest.mock import patch, MagicMock

# Set environment variable before importing the module
os.environ['EVENT_LOGGING_ENABLED'] = 'true'

from langhook.subscriptions.config import subscription_settings


def test_event_logging_enabled_config():
    """Test that event logging can be enabled via environment variable."""
    # Reload settings with environment variable set
    with patch.dict(os.environ, {'EVENT_LOGGING_ENABLED': 'true'}):
        from langhook.subscriptions.config import load_subscription_settings
        settings = load_subscription_settings()
        assert settings.event_logging_enabled is True

    with patch.dict(os.environ, {'EVENT_LOGGING_ENABLED': 'false'}):
        from langhook.subscriptions.config import load_subscription_settings
        settings = load_subscription_settings()
        assert settings.event_logging_enabled is False

    with patch.dict(os.environ, {'EVENT_LOGGING_ENABLED': '1'}):
        from langhook.subscriptions.config import load_subscription_settings
        settings = load_subscription_settings()
        assert settings.event_logging_enabled is True


@patch('langhook.subscriptions.event_logging.subscription_settings')
@patch('langhook.subscriptions.event_logging.db_service')
async def test_enabled_service_starts_correctly(mock_db_service, mock_settings):
    """Test that the service properly starts when enabled."""
    # Configure mocks to simulate enabled event logging
    mock_settings.event_logging_enabled = True
    mock_settings.nats_url = "nats://localhost:4222"
    mock_settings.nats_stream_events = "events"
    mock_settings.nats_consumer_group = "test_group"
    mock_db_service.create_event_logs_table.return_value = None
    
    from langhook.subscriptions.event_logging import EventLoggingService, EventLoggingConsumer
    
    service = EventLoggingService()
    
    with patch.object(EventLoggingConsumer, 'start') as mock_start:
        await service.start()
        
        # Verify service started correctly
        assert service._running is True
        assert service.consumer is not None
        mock_db_service.create_event_logs_table.assert_called_once()
        mock_start.assert_called_once()


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])