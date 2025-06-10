"""Integration test for DLQ handling end-to-end flow."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from langhook.app import send_to_dlq
from langhook.subscriptions.dlq_logging import dlq_logging_service


@pytest.mark.asyncio
async def test_dlq_end_to_end_flow():
    """Test end-to-end DLQ flow from send_to_dlq to logging."""
    # Test data
    source = "github"
    request_id = "test-error-123"
    body_bytes = b'{"invalid": json}'
    error = "Invalid JSON: Expecting property name enclosed in double quotes"
    headers = {"content-type": "application/json", "x-github-event": "pull_request"}

    # Mock NATS producer to capture DLQ message
    with patch('langhook.app.nats_producer') as mock_producer:
        # Mock the NATS producer send_dlq method
        mock_producer.send_dlq = AsyncMock()

        # Send to DLQ
        await send_to_dlq(source, request_id, body_bytes, error, headers)

        # Verify DLQ message was sent with correct structure
        mock_producer.send_dlq.assert_called_once()
        dlq_message = mock_producer.send_dlq.call_args[0][0]

        assert dlq_message["id"] == request_id
        assert dlq_message["source"] == source
        assert dlq_message["error"] == error
        assert dlq_message["headers"] == headers
        assert dlq_message["payload"] == '{"invalid": json}'
        assert "timestamp" in dlq_message

        # Now test that the DLQ logging service can process this message
        with patch('langhook.subscriptions.dlq_logging.db_service') as mock_db_service:
            mock_session = MagicMock()
            mock_db_service.get_session.return_value.__enter__.return_value = mock_session

            # Process the DLQ message through the logging service
            await dlq_logging_service._log_dlq_event(dlq_message)

            # Verify error event was logged correctly
            mock_session.add.assert_called_once()
            event_log = mock_session.add.call_args[0][0]

            # Verify the event log has correct error structure
            assert event_log.event_id == request_id
            assert event_log.source == source
            assert event_log.publisher == source
            assert event_log.resource_type == "webhook_failure"
            assert event_log.action == "failed"
            assert event_log.subject == f"dlq.{source}.{request_id}"

            # Verify error canonical data structure
            canonical_data = event_log.canonical_data
            assert canonical_data["error"] is True
            assert canonical_data["error_message"] == error
            assert canonical_data["error_type"] == "dlq_processing_failed"
            assert canonical_data["headers"] == headers

            # Verify raw payload handling
            assert event_log.raw_payload == {"raw_text": '{"invalid": json}'}

            mock_session.commit.assert_called_once()


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])