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
             patch('langhook.subscriptions.gate.llm_gate_service') as mock_gate, \
             patch('langhook.subscriptions.budget.budget_monitor') as mock_budget:
            
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
                "model": "gpt-4o-mini",
                "prompt": "security_focused",
                "threshold": 0.8,
                "audit": True,
                "failover_policy": "fail_open"
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

            # Mock gate service
            mock_gate.evaluate_event = AsyncMock(return_value=(True, "Security issue detected", 0.9))

            # Mock budget monitor
            mock_budget.record_cost = Mock()
            mock_budget.get_budget_status = Mock(return_value={
                "date": "2024-01-01",
                "daily_cost_usd": 2.50,
                "daily_limit_usd": 10.0,
                "percentage_used": 25.0,
                "status": "LOW_USAGE"
            })

            yield {
                "db": mock_db,
                "llm": mock_llm,
                "gate": mock_gate,
                "budget": mock_budget,
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
            "model": "gpt-4o-mini",
            "prompt": "security_focused",
            "threshold": 0.9,
            "audit": True,
            "failover_policy": "fail_closed"
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
        assert data["gate"]["model"] == "gpt-4o-mini"
        assert data["gate"]["prompt"] == "security_focused"
        assert data["gate"]["threshold"] == 0.9

        # Verify LLM service was called to generate pattern
        mock_services["llm"].convert_to_pattern.assert_called_once_with("Critical security alerts from GitHub")

        # Verify database service was called with gate config
        mock_services["db"].create_subscription.assert_called_once()

    def test_update_subscription_gate_config(self, client, mock_services):
        """Test updating a subscription's gate configuration."""
        new_gate_config = {
            "enabled": False,
            "model": "gpt-4",
            "prompt": "important_only",
            "threshold": 0.7,
            "audit": False,
            "failover_policy": "fail_open"
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

    def test_get_gate_budget_status(self, client, mock_services):
        """Test getting gate budget status."""
        response = client.get("/subscriptions/gate/budget")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "daily_cost_usd" in data
        assert "daily_limit_usd" in data
        assert "percentage_used" in data
        assert "status" in data
        
        # Verify budget monitor was called
        mock_services["budget"].get_budget_status.assert_called_once()

    def test_get_gate_templates(self, client, mock_services):
        """Test getting available gate templates."""
        with patch('langhook.subscriptions.prompts.prompt_library') as mock_prompts:
            mock_prompts.list_templates.return_value = {
                "default": "Default prompt...",
                "security_focused": "Security prompt...",
                "important_only": "Important prompt..."
            }

            response = client.get("/subscriptions/gate/templates")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "templates" in data
            assert "default_template" in data
            assert data["default_template"] == "default"
            assert len(data["templates"]) >= 3

    def test_reload_gate_templates(self, client, mock_services):
        """Test reloading gate templates."""
        with patch('langhook.subscriptions.prompts.prompt_library') as mock_prompts:
            mock_prompts.reload_templates = Mock()
            mock_prompts.list_templates.return_value = {
                "default": "Default prompt...",
                "new_template": "New prompt..."
            }

            response = client.post("/subscriptions/gate/templates/reload")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["message"] == "Templates reloaded successfully"
            assert "templates" in data
            
            # Verify reload was called
            mock_prompts.reload_templates.assert_called_once()

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
        # Test invalid threshold
        invalid_gate_config = {
            "enabled": True,
            "model": "gpt-4o-mini",
            "prompt": "default",
            "threshold": 1.5,  # Invalid - above 1.0
            "audit": True,
            "failover_policy": "fail_open"
        }

        subscription_data = {
            "description": "Test subscription",
            "gate": invalid_gate_config
        }

        response = client.post("/subscriptions/", json=subscription_data)
        
        # Should fail validation
        assert response.status_code == 422

    def test_gate_configuration_schema(self):
        """Test gate configuration schema validation."""
        # Valid config
        valid_config = GateConfig(
            enabled=True,
            model="gpt-4o-mini",
            prompt="security_focused",
            threshold=0.8,
            audit=True,
            failover_policy="fail_open"
        )
        
        assert valid_config.enabled is True
        assert valid_config.model == "gpt-4o-mini"
        assert valid_config.threshold == 0.8

        # Test defaults
        default_config = GateConfig()
        assert default_config.enabled is False
        assert default_config.model == "gpt-4o-mini"
        assert default_config.threshold == 0.8
        assert default_config.audit is True
        assert default_config.failover_policy == "fail_open"

        # Test invalid values
        with pytest.raises(ValueError):
            GateConfig(threshold=1.5)

        with pytest.raises(ValueError):
            GateConfig(failover_policy="invalid_policy")

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
                "model": "gpt-4o-mini",
                "prompt": "default",
                "threshold": 0.8,
                "audit": True,
                "failover_policy": "fail_open"
            },
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": None
        }

        response = SubscriptionResponse(**subscription_data)
        
        assert response.gate is not None
        assert response.gate["enabled"] is True
        assert response.gate["model"] == "gpt-4o-mini"