"""Test NATS consumer configuration for proper delivery policy."""

from unittest.mock import AsyncMock

from nats.js.api import DeliverPolicy

from langhook.map.nats import MapNATSConsumer


def test_map_nats_consumer_delivery_policy():
    """Test that MapNATSConsumer uses appropriate delivery policy for production use."""

    # Create a mock message handler
    mock_handler = AsyncMock()

    # Create the consumer
    consumer = MapNATSConsumer(mock_handler)

    # Verify the consumer has the correct delivery policy
    # For production systems that need to track message consumption properly,
    # the consumer should NOT use DeliverPolicy.ALL which reprocesses all messages
    # on every restart. It should use NEW or rely on durable consumer behavior.
    assert consumer.deliver_policy != DeliverPolicy.ALL, (
        "MapNATSConsumer should not use DeliverPolicy.ALL as it causes "
        "reprocessing of all events on every startup. Use DeliverPolicy.NEW "
        "or remove explicit policy to use durable consumer behavior."
    )


def test_map_nats_consumer_is_durable():
    """Test that MapNATSConsumer is configured as a durable consumer."""

    # Create a mock message handler
    mock_handler = AsyncMock()

    # Create the consumer
    consumer = MapNATSConsumer(mock_handler)

    # Verify that the consumer has a consumer name (making it durable)
    assert consumer.consumer_name is not None
    assert len(consumer.consumer_name) > 0

    # Verify the consumer name follows expected pattern
    assert "raw_processor" in consumer.consumer_name

    # For durable consumers, the delivery policy should not override
    # the consumer's ability to track its position in the stream
    assert consumer.deliver_policy in [DeliverPolicy.NEW, DeliverPolicy.LAST_PER_SUBJECT]


def test_map_nats_consumer_initialization():
    """Test that MapNATSConsumer initializes with correct parameters."""

    mock_handler = AsyncMock()
    consumer = MapNATSConsumer(mock_handler)

    # Verify basic initialization
    assert consumer.message_handler == mock_handler
    assert consumer.filter_subject == "raw.>"
    assert consumer.stream_name == "events"  # default from settings

    # Verify NATS URL and other settings
    assert consumer.nats_url == "nats://localhost:4222"  # default from settings
