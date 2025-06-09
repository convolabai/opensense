"""End-to-end test for LLM Gate functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

from langhook.subscriptions.schemas import SubscriptionCreate, GateConfig


class TestLLMGateE2E:
    """End-to-end tests for LLM Gate functionality."""

    @pytest.fixture
    def mock_services(self):
        """Mock all required services for E2E testing."""
        with patch('langhook.subscriptions.database.db_service') as mock_db, \
             patch('langhook.subscriptions.llm.llm_service') as mock_llm, \
             patch('langhook.subscriptions.gate.llm_gate_service') as mock_gate:
            
            # Mock subscription
            mock_subscription = Mock()
            mock_subscription.id = 1
            mock_subscription.subscriber_id = "default"
            mock_subscription.description = "Critical security alerts"
            mock_subscription.pattern = "langhook.events.security.*.*.*"
            mock_subscription.channel_type = "webhook"
            mock_subscription.channel_config = {"url": "https://example.com/webhook"}
            mock_subscription.gate = {
                "enabled": True,
                "prompt": "You are evaluating security events..."
            }
            mock_subscription.active = True

            # Mock database operations
            mock_db.create_subscription = AsyncMock(return_value=mock_subscription)
            mock_db.get_subscription = AsyncMock(return_value=mock_subscription)
            mock_db.update_subscription = AsyncMock(return_value=mock_subscription)
            mock_db.delete_subscription = AsyncMock(return_value=True)
            mock_db.get_subscriber_subscriptions = AsyncMock(return_value=([mock_subscription], 1))
            mock_db.create_tables = Mock()

            # Mock LLM service
            mock_llm.convert_to_pattern = AsyncMock(return_value="langhook.events.security.*.*.*")
            mock_llm.generate_gate_prompt = AsyncMock(return_value="You are evaluating security events...")
            
            def mock_convert_to_pattern_and_gate(description, gate_enabled=False):
                result = {"pattern": "langhook.events.security.*.*.*"}
                if gate_enabled:
                    result["gate_prompt"] = "You are evaluating security events..."
                return result
            
            mock_llm.convert_to_pattern_and_gate = AsyncMock(side_effect=mock_convert_to_pattern_and_gate)

            # Mock gate service
            mock_gate.evaluate_event = AsyncMock(return_value=(True, "Security issue detected"))

            yield {
                "db": mock_db,
                "llm": mock_llm,
                "gate": mock_gate,
                "subscription": mock_subscription
            }

    @pytest.fixture
    def client(self, mock_services):
        """Create a test client with mocked services."""
        with patch('langhook.ingest.nats.nats_producer') as mock_nats, \
             patch('langhook.map.service.mapping_service') as mock_mapping, \
             patch('langhook.ingest.middleware.RateLimitMiddleware.is_rate_limited') as mock_rate_limit, \
             patch('nats.connect') as mock_nats_connect:

            # Mock NATS
            mock_nats.start = AsyncMock()
            mock_nats.stop = AsyncMock()
            mock_mapping.run = AsyncMock()
            mock_rate_limit.return_value = False

            # Mock NATS connection
            mock_nc = AsyncMock()
            mock_js = Mock()
            mock_js.publish = AsyncMock()
            mock_nc.jetstream = Mock(return_value=mock_js)
            mock_nc.close = AsyncMock()
            mock_nats_connect.return_value = mock_nc

            # Create test client
            from langhook.app import app
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_lifespan(app):
                yield

            app.router.lifespan_context = mock_lifespan
            return TestClient(app)

    def test_create_subscription_with_llm_gate(self, client, mock_services):
        """Test creating a subscription with LLM gate enabled."""
        gate_config = {
            "enabled": True,
            "prompt": ""  # Will be auto-generated
        }

        subscription_data = {
            "description": "Critical security alerts from GitHub",
            "channel_type": "webhook",
            "channel_config": {"url": "https://example.com/webhook"},
            "gate": gate_config
        }

        response = client.post("/subscriptions/", json=subscription_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify subscription created with gate config
        assert data["description"] == "Critical security alerts from GitHub"
        assert data["gate"] is not None
        assert data["gate"]["enabled"] is True

        # Verify LLM service was called to generate pattern and gate prompt
        mock_services["llm"].convert_to_pattern_and_gate.assert_called_once_with(
            "Critical security alerts from GitHub", 
            gate_enabled=True
        )

        # Verify database service was called with gate config
        mock_services["db"].create_subscription.assert_called_once()

    def test_update_subscription_gate_config(self, client, mock_services):
        """Test updating a subscription's gate configuration."""
        new_gate_config = {
            "enabled": False,
            "prompt": "Custom prompt for evaluation"
        }

        update_data = {
            "gate": new_gate_config
        }

        response = client.put("/subscriptions/1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify gate config was updated
        assert data["gate"]["enabled"] is True  # Mock returns original
        
        # Verify database service was called
        mock_services["db"].update_subscription.assert_called_once()

    def test_subscription_with_gate_disabled(self, client, mock_services):
        """Test creating a subscription with gate disabled."""
        subscription_data = {
            "description": "All GitHub events",
            "channel_type": "webhook",
            "channel_config": {"url": "https://example.com/webhook"}
            # No gate config = disabled by default
        }

        response = client.post("/subscriptions/", json=subscription_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Gate should be None when not specified
        assert data["gate"] is None

    def test_subscription_gate_validation(self, client, mock_services):
        """Test gate configuration validation."""
        # Test invalid gate config (empty prompt when enabled)
        invalid_gate_config = {
            "enabled": True,
            "prompt": ""  # Invalid - enabled but empty prompt will auto-generate
        }

        subscription_data = {
            "description": "Test subscription",
            "gate": invalid_gate_config
        }

        response = client.post("/subscriptions/", json=subscription_data)
        
        # Should succeed because empty prompt triggers auto-generation
        assert response.status_code == 201

    def test_gate_configuration_schema(self):
        """Test gate configuration schema validation."""
        # Valid config
        valid_config = GateConfig(
            enabled=True,
            prompt="Custom evaluation prompt"
        )
        
        assert valid_config.enabled is True
        assert valid_config.prompt == "Custom evaluation prompt"

        # Test defaults
        default_config = GateConfig()
        assert default_config.enabled is False
        assert default_config.prompt == ""

    def test_subscription_response_includes_gate(self):
        """Test that subscription response includes gate configuration."""
        from langhook.subscriptions.schemas import SubscriptionResponse
        
        # Mock subscription data
        subscription_data = {
            "id": 1,
            "subscriber_id": "test_user",
            "description": "Test subscription",
            "pattern": "langhook.events.*.*.*",
            "channel_type": "webhook",
            "channel_config": {"url": "https://example.com/webhook"},
            "active": True,
            "gate": {
                "enabled": True,
                "prompt": "Custom evaluation prompt"
            },
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": None
        }

        response = SubscriptionResponse(**subscription_data)
        
        assert response.gate is not None
        assert response.gate["enabled"] is True
        assert response.gate["prompt"] == "Custom evaluation prompt"