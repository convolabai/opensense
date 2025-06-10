"""Tests for DLQ logging functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langhook.subscriptions.dlq_logging import DLQLoggingConsumer, DLQLoggingService
from langhook.subscriptions.models import EventLog


@pytest.fixture
def sample_dlq_event():
    """Sample DLQ event for testing."""
    return {
        "id": "test-dlq-123",
        "timestamp": "2023-12-01T12:00:00Z",
        "source": "github",
        "error": "Invalid JSON: Expecting property name enclosed in double quotes",
        "headers": {
            "content-type": "application/json",
            "x-github-event": "pull_request"
        },
        "payload": '{"invalid": json}'
    }


@pytest.fixture
def dlq_logging_service():
    """DLQ logging service for testing."""
    return DLQLoggingService()


class TestDLQLoggingService:
    """Test the DLQLoggingService class."""

    async def test_start_when_disabled(self, dlq_logging_service):
        """Test service start when event logging is disabled."""
        with patch('langhook.subscriptions.dlq_logging.subscription_settings') as mock_settings:
            mock_settings.event_logging_enabled = False

            await dlq_logging_service.start()

            assert dlq_logging_service.consumer is None
            assert not dlq_logging_service._running

    @patch('langhook.subscriptions.dlq_logging.db_service')
    async def test_start_when_enabled(self, mock_db_service, dlq_logging_service):
        """Test service start when event logging is enabled."""
        with patch('langhook.subscriptions.dlq_logging.subscription_settings') as mock_settings:
            mock_settings.event_logging_enabled = True

            with patch('langhook.subscriptions.dlq_logging.DLQLoggingConsumer') as mock_consumer_class:
                mock_consumer = AsyncMock()
                mock_consumer_class.return_value = mock_consumer

                await dlq_logging_service.start()

                assert dlq_logging_service.consumer is not None
                assert dlq_logging_service._running
                mock_db_service.create_event_logs_table.assert_called_once()
                mock_consumer.start.assert_called_once()

    async def test_run_when_disabled(self, dlq_logging_service):
        """Test service run when event logging is disabled."""
        with patch('langhook.subscriptions.dlq_logging.subscription_settings') as mock_settings:
            mock_settings.event_logging_enabled = False

            await dlq_logging_service.run()

            assert dlq_logging_service.consumer is None
            assert not dlq_logging_service._running

    @patch('langhook.subscriptions.dlq_logging.db_service')
    async def test_log_dlq_event_success(self, mock_db_service, sample_dlq_event, dlq_logging_service):
        """Test successful DLQ event logging."""
        # Mock database session
        mock_session = MagicMock()
        mock_db_service.get_session.return_value.__enter__.return_value = mock_session

        await dlq_logging_service._log_dlq_event(sample_dlq_event)

        # Verify event log was created with error structure
        mock_session.add.assert_called_once()
        event_log = mock_session.add.call_args[0][0]

        assert isinstance(event_log, EventLog)
        assert event_log.event_id == "test-dlq-123"
        assert event_log.source == "github"
        assert event_log.publisher == "github"
        assert event_log.resource_type == "webhook_failure"
        assert event_log.action == "failed"
        assert event_log.canonical_data["error"] is True
        assert event_log.canonical_data["error_message"] == "Invalid JSON: Expecting property name enclosed in double quotes"
        assert event_log.canonical_data["error_type"] == "dlq_processing_failed"

    async def test_log_dlq_event_missing_id(self, dlq_logging_service):
        """Test DLQ event logging with missing ID."""
        invalid_event = {
            "timestamp": "2023-12-01T12:00:00Z",
            "source": "github",
            "error": "Some error",
            "headers": {},
            "payload": ""
        }

        # Should not raise an exception, just log a warning
        await dlq_logging_service._log_dlq_event(invalid_event)

    async def test_log_dlq_event_invalid_json_payload(self, dlq_logging_service):
        """Test DLQ event logging with invalid JSON payload."""
        dlq_event = {
            "id": "test-dlq-123",
            "timestamp": "2023-12-01T12:00:00Z",
            "source": "github",
            "error": "Invalid JSON",
            "headers": {},
            "payload": '{"invalid": json}'  # Invalid JSON
        }

        with patch('langhook.subscriptions.dlq_logging.db_service') as mock_db_service:
            mock_session = MagicMock()
            mock_db_service.get_session.return_value.__enter__.return_value = mock_session

            await dlq_logging_service._log_dlq_event(dlq_event)

            # Should still create event log with raw_text payload
            mock_session.add.assert_called_once()
            event_log = mock_session.add.call_args[0][0]
            assert event_log.raw_payload == {"raw_text": '{"invalid": json}'}

    @patch('langhook.subscriptions.dlq_logging.db_service')
    async def test_log_dlq_event_database_error(self, mock_db_service, sample_dlq_event, dlq_logging_service):
        """Test DLQ event logging when database error occurs."""
        # Mock database error
        mock_db_service.get_session.side_effect = Exception("Database connection failed")

        # Should not raise an exception, just log the error
        await dlq_logging_service._log_dlq_event(sample_dlq_event)


class TestDLQLoggingConsumer:
    """Test the DLQLoggingConsumer class."""

    def test_consumer_initialization(self):
        """Test DLQ consumer initialization."""
        message_handler = AsyncMock()

        with patch('langhook.subscriptions.dlq_logging.subscription_settings') as mock_settings:
            mock_settings.nats_url = "nats://localhost:4222"
            mock_settings.nats_stream_events = "events"
            mock_settings.nats_consumer_group = "test_group"

            consumer = DLQLoggingConsumer(message_handler)

            assert consumer.filter_subject == "dlq.>"
            assert consumer.consumer_name == "test_group_dlq_logger"
            assert consumer.message_handler == message_handler


@pytest.mark.asyncio
async def test_dlq_logging_integration():
    """Integration test for DLQ logging with mocked dependencies."""
    dlq_event = {
        "id": "integration-test-123",
        "timestamp": "2023-12-01T12:00:00Z",
        "source": "stripe",
        "error": "Webhook signature verification failed",
        "headers": {"content-type": "application/json"},
        "payload": '{"event": "payment.failed"}'
    }

    service = DLQLoggingService()

    with patch('langhook.subscriptions.dlq_logging.subscription_settings') as mock_settings:
        mock_settings.event_logging_enabled = True
        mock_settings.nats_url = "nats://localhost:4222"
        mock_settings.nats_stream_events = "events"
        mock_settings.nats_consumer_group = "test_group"

        with patch('langhook.subscriptions.dlq_logging.db_service') as mock_db_service:
            mock_session = MagicMock()
            mock_db_service.get_session.return_value.__enter__.return_value = mock_session

            await service._log_dlq_event(dlq_event)

            # Verify error event was logged correctly
            mock_session.add.assert_called_once()
            event_log = mock_session.add.call_args[0][0]

            assert event_log.event_id == "integration-test-123"
            assert event_log.source == "stripe"
            assert event_log.canonical_data["error"] is True
            assert event_log.canonical_data["error_message"] == "Webhook signature verification failed"
            assert event_log.raw_payload == {"event": "payment.failed"}


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
