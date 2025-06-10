"""Test subscription creation and updates with LLM Gate configuration."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from langhook.subscriptions.database import DatabaseService
from langhook.subscriptions.schemas import SubscriptionCreate, SubscriptionUpdate, GateConfig
from langhook.subscriptions.models import Subscription


class TestSubscriptionWithGate:
    """Test subscription operations with LLM Gate configuration."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service for testing."""
        with patch('langhook.subscriptions.database.db_service') as mock_db:
            # Setup mock subscription object
            mock_subscription = Mock(spec=Subscription)
            mock_subscription.id = 1
            mock_subscription.subscriber_id = "test_user"
            mock_subscription.description = "Important GitHub pull requests"
            mock_subscription.pattern = "langhook.events.github.pull_request.*.*"
            mock_subscription.channel_type = "webhook"
            mock_subscription.channel_config = {"url": "https://example.com/webhook"}
            mock_subscription.gate = {
                "enabled": True,
                "prompt": "You are evaluating GitHub events for importance..."
            }
            mock_subscription.active = True

            mock_db.create_subscription = AsyncMock(return_value=mock_subscription)
            mock_db.update_subscription = AsyncMock(return_value=mock_subscription)
            mock_db.get_subscription = AsyncMock(return_value=mock_subscription)
            
            yield mock_db

    @pytest.mark.asyncio
    async def test_create_subscription_with_gate(self, mock_db_service):
        """Test creating a subscription with LLM gate configuration."""
        gate_config = GateConfig(
            enabled=True,
            prompt="Custom evaluation prompt for important events"
        )
        
        subscription_data = SubscriptionCreate(
            description="Important GitHub pull requests",
            channel_type="webhook",
            channel_config={"url": "https://example.com/webhook"},
            gate=gate_config
        )

        # Test creation
        result = await mock_db_service.create_subscription(
            subscriber_id="test_user",
            pattern="langhook.events.github.pull_request.*.*",
            subscription_data=subscription_data
        )

        # Verify the call was made with correct gate data
        mock_db_service.create_subscription.assert_called_once()
        call_args = mock_db_service.create_subscription.call_args
        assert call_args[1]["subscription_data"].gate.enabled is True
        assert call_args[1]["subscription_data"].gate.prompt == "Custom evaluation prompt for important events"

    @pytest.mark.asyncio
    async def test_update_subscription_gate_config(self, mock_db_service):
        """Test updating a subscription's gate configuration."""
        new_gate_config = GateConfig(
            enabled=False,
            prompt="Updated evaluation prompt"
        )
        
        update_data = SubscriptionUpdate(
            gate=new_gate_config
        )

        # Test update
        result = await mock_db_service.update_subscription(
            subscription_id=1,
            subscriber_id="test_user",
            pattern=None,
            update_data=update_data
        )

        # Verify the call was made with correct gate data
        mock_db_service.update_subscription.assert_called_once()
        call_args = mock_db_service.update_subscription.call_args
        assert call_args[1]["update_data"].gate.enabled is False
        assert call_args[1]["update_data"].gate.prompt == "Updated evaluation prompt"

    @pytest.mark.asyncio
    async def test_create_subscription_without_gate(self, mock_db_service):
        """Test creating a subscription without gate configuration."""
        subscription_data = SubscriptionCreate(
            description="All GitHub events",
            channel_type="webhook",
            channel_config={"url": "https://example.com/webhook"}
            # No gate config
        )

        result = await mock_db_service.create_subscription(
            subscriber_id="test_user",
            pattern="langhook.events.github.*.*.*",
            subscription_data=subscription_data
        )

        # Verify the call was made without gate data
        mock_db_service.create_subscription.assert_called_once()
        call_args = mock_db_service.create_subscription.call_args
        assert call_args[1]["subscription_data"].gate is None

    def test_gate_config_schema_validation(self):
        """Test that GateConfig validates correctly."""
        # Valid config
        valid_config = GateConfig(
            enabled=True,
            prompt="Custom evaluation prompt"
        )
        
        assert valid_config.enabled is True
        assert valid_config.prompt == "Custom evaluation prompt"
        
        # Test default values
        default_config = GateConfig()
        assert default_config.enabled is False
        assert default_config.prompt == ""


class TestSubscriptionConsumerWithGate:
    """Test subscription consumer with LLM gate evaluation."""

    @pytest.fixture
    def mock_subscription_with_gate(self):
        """Mock subscription with gate enabled."""
        subscription = Mock(spec=Subscription)
        subscription.id = 1
        subscription.subscriber_id = "test_user"
        subscription.description = "Important GitHub pull requests"
        subscription.pattern = "langhook.events.github.pull_request.*.*"
        subscription.channel_type = "webhook"
        subscription.channel_config = {"url": "https://example.com/webhook"}
        subscription.gate = {
            "enabled": True,
            "prompt": "Evaluate GitHub events for importance..."
        }
        subscription.active = True
        return subscription

    @pytest.fixture
    def mock_subscription_without_gate(self):
        """Mock subscription without gate enabled."""
        subscription = Mock(spec=Subscription)
        subscription.id = 2
        subscription.subscriber_id = "test_user"
        subscription.description = "All GitHub events"
        subscription.pattern = "langhook.events.github.*.*.*"
        subscription.channel_type = "webhook"
        subscription.channel_config = {"url": "https://example.com/webhook"}
        subscription.gate = None
        subscription.active = True
        return subscription

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "id": "test_event_123",
            "source": "github",
            "subject": "langhook.events.github.pull_request.123.created",
            "data": {
                "publisher": "github",
                "resource": {"type": "pull_request", "id": 123},
                "action": "created",
                "timestamp": "2024-01-01T12:00:00Z",
                "payload": {
                    "title": "Fix critical security vulnerability",
                    "author": "security@example.com",
                    "priority": "critical"
                }
            }
        }

    @pytest.mark.asyncio
    async def test_consumer_processes_event_with_gate_pass(
        self, 
        mock_subscription_with_gate, 
        sample_event_data
    ):
        """Test that consumer processes event when gate passes."""
        from langhook.subscriptions.consumer_service import SubscriptionConsumer
        
        with patch('langhook.subscriptions.consumer_service.llm_gate_service') as mock_gate, \
             patch('langhook.subscriptions.consumer_service.db_service') as mock_db, \
             patch('httpx.AsyncClient') as mock_http:
            
            # Mock gate passes
            mock_gate.evaluate_event = AsyncMock(return_value=(True, "Important security fix"))
            
            # Mock database save
            mock_db.get_session = Mock()
            mock_db.get_session.return_value.__enter__ = Mock()
            mock_db.get_session.return_value.__exit__ = Mock()
            
            # Mock successful webhook
            mock_response = Mock()
            mock_response.status_code = 200
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
            mock_http.return_value.__aexit__ = AsyncMock()
            mock_http.return_value.post = AsyncMock(return_value=mock_response)

            consumer = SubscriptionConsumer(mock_subscription_with_gate)
            await consumer._handle_subscription_event(sample_event_data)

            # Verify gate was called
            mock_gate.evaluate_event.assert_called_once()
            gate_call_args = mock_gate.evaluate_event.call_args[1]
            assert gate_call_args["subscription_id"] == 1
            assert gate_call_args["gate_config"] == mock_subscription_with_gate.gate

            # Verify webhook was sent (since gate passed)
            mock_http.return_value.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_consumer_blocks_event_when_gate_fails(
        self, 
        mock_subscription_with_gate, 
        sample_event_data
    ):
        """Test that consumer blocks event when gate fails."""
        from langhook.subscriptions.consumer_service import SubscriptionConsumer
        
        with patch('langhook.subscriptions.consumer_service.llm_gate_service') as mock_gate, \
             patch('langhook.subscriptions.consumer_service.db_service') as mock_db, \
             patch('httpx.AsyncClient') as mock_http:
            
            # Mock gate blocks
            mock_gate.evaluate_event = AsyncMock(return_value=(False, "Not relevant enough"))
            
            # Mock database save
            mock_db.get_session = Mock()
            mock_db.get_session.return_value.__enter__ = Mock()
            mock_db.get_session.return_value.__exit__ = Mock()

            consumer = SubscriptionConsumer(mock_subscription_with_gate)
            await consumer._handle_subscription_event(sample_event_data)

            # Verify gate was called
            mock_gate.evaluate_event.assert_called_once()

            # Verify webhook was NOT sent (since gate blocked)
            mock_http.return_value.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_bypasses_gate_when_disabled(
        self, 
        mock_subscription_without_gate, 
        sample_event_data
    ):
        """Test that consumer bypasses gate when not enabled."""
        from langhook.subscriptions.consumer_service import SubscriptionConsumer
        
        with patch('langhook.subscriptions.consumer_service.llm_gate_service') as mock_gate, \
             patch('langhook.subscriptions.consumer_service.db_service') as mock_db, \
             patch('httpx.AsyncClient') as mock_http:
            
            # Mock database save
            mock_db.get_session = Mock()
            mock_db.get_session.return_value.__enter__ = Mock()
            mock_db.get_session.return_value.__exit__ = Mock()
            
            # Mock successful webhook
            mock_response = Mock()
            mock_response.status_code = 200
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
            mock_http.return_value.__aexit__ = AsyncMock()
            mock_http.return_value.post = AsyncMock(return_value=mock_response)

            consumer = SubscriptionConsumer(mock_subscription_without_gate)
            await consumer._handle_subscription_event(sample_event_data)

            # Verify gate was NOT called
            mock_gate.evaluate_event.assert_not_called()

            # Verify webhook was sent (no gate to block)
            mock_http.return_value.post.assert_called_once()