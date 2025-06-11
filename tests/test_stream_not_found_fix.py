"""Tests for stream not found error fix."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langhook.core.nats import BaseNATSConsumer


class TestStreamNotFoundFix:
    """Test the fix for stream not found errors."""

    @pytest.fixture
    def consumer(self):
        """Create a test consumer."""
        message_handler = AsyncMock()
        return BaseNATSConsumer(
            nats_url="nats://localhost:4222",
            stream_name="test_stream",
            consumer_name="test_consumer",
            filter_subject="test.>",
            message_handler=message_handler,
        )

    async def test_wait_for_stream_success_immediate(self, consumer):
        """Test stream verification succeeds immediately."""
        # Set up the mock JS context
        consumer.js = AsyncMock()
        consumer.js.stream_info.return_value = MagicMock()
        
        # Should return without error
        await consumer._wait_for_stream()
        
        # Verify stream_info was called
        consumer.js.stream_info.assert_called_once_with("test_stream")

    async def test_wait_for_stream_success_after_retries(self, consumer):
        """Test stream verification succeeds after a few retries."""
        # Set up the mock JS context
        consumer.js = AsyncMock()
        # First two calls fail, third succeeds
        consumer.js.stream_info.side_effect = [
            Exception("stream not found"),
            Exception("stream not found"),
            MagicMock(),  # Success on third try
        ]
        
        # Should return without error after retries
        await consumer._wait_for_stream(max_retries=5, initial_delay=0.01)
        
        # Verify stream_info was called 3 times
        assert consumer.js.stream_info.call_count == 3

    async def test_wait_for_stream_fails_after_max_retries(self, consumer):
        """Test stream verification fails after max retries."""
        # Set up the mock JS context
        consumer.js = AsyncMock()
        consumer.js.stream_info.side_effect = Exception("stream not found")
        
        # Should raise RuntimeError after max retries
        with pytest.raises(RuntimeError, match="Stream 'test_stream' not found after 3 attempts"):
            await consumer._wait_for_stream(max_retries=3, initial_delay=0.01)
        
        # Verify stream_info was called max_retries times
        assert consumer.js.stream_info.call_count == 3

    async def test_wait_for_stream_fails_immediately_on_other_error(self, consumer):
        """Test stream verification fails immediately on non-stream-not-found errors."""
        # Set up the mock JS context
        consumer.js = AsyncMock()
        consumer.js.stream_info.side_effect = Exception("connection error")
        
        # Should raise the original exception immediately
        with pytest.raises(Exception, match="connection error"):
            await consumer._wait_for_stream()
        
        # Verify stream_info was called only once (no retries)
        assert consumer.js.stream_info.call_count == 1


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])