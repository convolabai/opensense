"""Tests for LLM Gate functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from langhook.subscriptions.gate import LLMGateService
from langhook.subscriptions.schemas import GateConfig
from langhook.subscriptions.prompts import PromptLibrary


class TestLLMGateService:
    """Test LLM Gate service functionality."""

    @pytest.fixture
    def gate_service(self):
        """Create a gate service for testing."""
        service = LLMGateService()
        service.llm_service = Mock()
        service.llm_service.is_available.return_value = True
        service.llm_service.llm = AsyncMock()
        return service

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 123},
            "action": "created",
            "timestamp": "2024-01-01T12:00:00Z",
            "payload": {
                "title": "Fix critical bug in user authentication",
                "author": "dev@example.com",
                "priority": "high"
            }
        }

    @pytest.fixture
    def gate_config(self):
        """Sample gate configuration."""
        return {
            "enabled": True,
            "model": "gpt-4o-mini",
            "prompt": "Is this event important?",
            "threshold": 0.8,
            "audit": True,
            "failover_policy": "fail_open"
        }

    @pytest.mark.asyncio
    async def test_evaluate_event_passes_gate(self, gate_service, sample_event_data, gate_config):
        """Test that an important event passes the gate."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"decision": true, "confidence": 0.9, "reasoning": "This is a critical bug fix"}'
        gate_service.llm_service.llm.ainvoke.return_value = mock_response

        should_pass, reason, confidence = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_description="Important GitHub pull requests",
            subscription_id=1
        )

        assert should_pass is True
        assert confidence == 0.9
        assert "critical bug fix" in reason

    @pytest.mark.asyncio
    async def test_evaluate_event_blocks_gate(self, gate_service, sample_event_data, gate_config):
        """Test that an unimportant event is blocked by the gate."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"decision": false, "confidence": 0.3, "reasoning": "This is not important"}'
        gate_service.llm_service.llm.ainvoke.return_value = mock_response

        should_pass, reason, confidence = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_description="Important GitHub pull requests",
            subscription_id=1
        )

        assert should_pass is False
        assert confidence == 0.3
        assert "not important" in reason

    @pytest.mark.asyncio
    async def test_evaluate_event_threshold_filtering(self, gate_service, sample_event_data, gate_config):
        """Test that threshold filtering works correctly."""
        # Set high threshold
        gate_config["threshold"] = 0.9
        
        # Mock LLM response with decision=true but low confidence
        mock_response = Mock()
        mock_response.content = '{"decision": true, "confidence": 0.7, "reasoning": "Somewhat important"}'
        gate_service.llm_service.llm.ainvoke.return_value = mock_response

        should_pass, reason, confidence = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_description="Important GitHub pull requests",
            subscription_id=1
        )

        # Should be blocked due to confidence below threshold
        assert should_pass is False
        assert confidence == 0.7

    @pytest.mark.asyncio
    async def test_failover_policy_fail_open(self, gate_service, sample_event_data, gate_config):
        """Test fail-open policy when LLM is unavailable."""
        gate_service.llm_service.is_available.return_value = False

        should_pass, reason, confidence = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_description="Important GitHub pull requests",
            subscription_id=1
        )

        assert should_pass is True
        assert "unavailable" in reason
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_failover_policy_fail_closed(self, gate_service, sample_event_data, gate_config):
        """Test fail-closed policy when LLM is unavailable."""
        gate_service.llm_service.is_available.return_value = False
        gate_config["failover_policy"] = "fail_closed"

        should_pass, reason, confidence = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_description="Important GitHub pull requests",
            subscription_id=1
        )

        assert should_pass is False
        assert "unavailable" in reason
        assert confidence == 0.0

    def test_parse_llm_response_valid_json(self, gate_service):
        """Test parsing of valid LLM JSON response."""
        response = '{"decision": true, "confidence": 0.8, "reasoning": "Important event"}'
        
        parsed = gate_service._parse_llm_response(response)
        
        assert parsed["decision"] is True
        assert parsed["confidence"] == 0.8
        assert parsed["reasoning"] == "Important event"

    def test_parse_llm_response_with_code_blocks(self, gate_service):
        """Test parsing of LLM response with JSON code blocks."""
        response = '''Here's my analysis:

```json
{"decision": false, "confidence": 0.2, "reasoning": "Not relevant"}
```

Hope this helps!'''
        
        parsed = gate_service._parse_llm_response(response)
        
        assert parsed["decision"] is False
        assert parsed["confidence"] == 0.2
        assert parsed["reasoning"] == "Not relevant"

    def test_parse_llm_response_invalid_json(self, gate_service):
        """Test parsing of invalid LLM response."""
        response = "This is not JSON at all!"
        
        parsed = gate_service._parse_llm_response(response)
        
        # Should return safe defaults
        assert parsed["decision"] is False
        assert parsed["confidence"] == 0.0
        assert "Failed to parse" in parsed["reasoning"]

    def test_get_default_prompt(self, gate_service):
        """Test default prompt generation."""
        description = "Important GitHub pull requests"
        
        prompt = gate_service._get_default_prompt(description)
        
        assert description in prompt
        assert "JSON object" in prompt
        assert "decision" in prompt
        assert "confidence" in prompt
        assert "reasoning" in prompt

    def test_estimate_cost(self, gate_service):
        """Test cost estimation."""
        prompt = "This is a test prompt" * 100  # Make it longer
        response = "This is a response" * 50
        model = "gpt-4o-mini"
        
        cost = gate_service._estimate_cost(prompt, response, model)
        
        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_cost_unknown_model(self, gate_service):
        """Test cost estimation for unknown model."""
        prompt = "Test prompt"
        response = "Test response"
        model = "unknown-model"
        
        cost = gate_service._estimate_cost(prompt, response, model)
        
        # Should default to gpt-4o-mini pricing
        assert cost > 0
        assert isinstance(cost, float)


class TestGateConfigSchema:
    """Test gate configuration schema validation."""

    def test_gate_config_defaults(self):
        """Test that gate config has proper defaults."""
        config = GateConfig()
        
        assert config.enabled is False
        assert config.model == "gpt-4o-mini"
        assert config.threshold == 0.8
        assert config.audit is True
        assert config.failover_policy == "fail_open"

    def test_gate_config_validation(self):
        """Test gate config validation."""
        # Valid config
        config = GateConfig(
            enabled=True,
            model="gpt-4",
            prompt="Test prompt",
            threshold=0.9,
            audit=False,
            failover_policy="fail_closed"
        )
        
        assert config.enabled is True
        assert config.model == "gpt-4"
        assert config.threshold == 0.9
        assert config.failover_policy == "fail_closed"

    def test_gate_config_invalid_threshold(self):
        """Test that invalid threshold values are rejected."""
        with pytest.raises(ValueError):
            GateConfig(threshold=1.5)  # Above 1.0
            
        with pytest.raises(ValueError):
            GateConfig(threshold=-0.1)  # Below 0.0

    def test_gate_config_invalid_failover_policy(self):
        """Test that invalid failover policy is rejected."""
        with pytest.raises(ValueError):
            GateConfig(failover_policy="invalid_policy")


class TestPromptLibrary:
    """Test prompt library functionality."""

    def test_prompt_library_loads_defaults(self):
        """Test that prompt library loads default templates."""
        library = PromptLibrary()
        
        assert "default" in library.templates
        assert "important_only" in library.templates
        assert "high_value" in library.templates
        assert "security_focused" in library.templates

    def test_get_template(self):
        """Test getting a template by name."""
        library = PromptLibrary()
        
        default_template = library.get_template("default")
        assert "intelligent event filter" in default_template.lower()
        assert "{description}" in default_template
        assert "{event_data}" in default_template

    def test_get_nonexistent_template(self):
        """Test getting a non-existent template returns default."""
        library = PromptLibrary()
        
        template = library.get_template("nonexistent")
        assert template == library.get_template("default")

    def test_list_templates(self):
        """Test listing all templates."""
        library = PromptLibrary()
        
        templates = library.list_templates()
        assert isinstance(templates, dict)
        assert "default" in templates
        
        # Should be truncated summaries
        for summary in templates.values():
            assert len(summary) <= 103  # 100 + "..."