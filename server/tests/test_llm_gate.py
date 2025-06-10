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
            "prompt": "You are evaluating whether this event matches the user's intent. Return only {\"decision\": true/false}. Event: {event_data}"
        }

    @pytest.mark.asyncio
    async def test_evaluate_event_passes_gate(self, gate_service, sample_event_data, gate_config):
        """Test that an important event passes the gate."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"decision": true}'
        gate_service.llm_service.llm.ainvoke.return_value = mock_response

        should_pass, reason = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_id=1
        )

        assert should_pass is True
        assert reason is not None

    @pytest.mark.asyncio
    async def test_evaluate_event_blocks_gate(self, gate_service, sample_event_data, gate_config):
        """Test that an unimportant event is blocked by the gate."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"decision": false}'
        gate_service.llm_service.llm.ainvoke.return_value = mock_response

        should_pass, reason = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_id=1
        )

        assert should_pass is False
        assert reason is not None

    @pytest.mark.asyncio
    async def test_failover_policy_fail_open(self, gate_service, sample_event_data, gate_config):
        """Test fail-open policy when LLM is unavailable."""
        gate_service.llm_service.is_available.return_value = False

        should_pass, reason = await gate_service.evaluate_event(
            event_data=sample_event_data,
            gate_config=gate_config,
            subscription_id=1
        )

        assert should_pass is True
        assert "unavailable" in reason

    def test_parse_llm_response_valid_json(self, gate_service):
        """Test parsing of valid LLM JSON response."""
        response = '{"decision": true}'
        
        parsed = gate_service._parse_llm_response(response)
        
        assert parsed["decision"] is True
        assert "reasoning" in parsed

    def test_parse_llm_response_with_code_blocks(self, gate_service):
        """Test parsing of LLM response with JSON code blocks."""
        response = '''Here's my analysis:

```json
{"decision": false}
```

Hope this helps!'''
        
        parsed = gate_service._parse_llm_response(response)
        
        assert parsed["decision"] is False
        assert "reasoning" in parsed

    def test_parse_llm_response_invalid_json(self, gate_service):
        """Test parsing of invalid LLM response."""
        response = "This is not JSON at all!"
        
        parsed = gate_service._parse_llm_response(response)
        
        # Should return safe defaults
        assert parsed["decision"] is False
        assert "Failed to parse" in parsed["reasoning"]

    def test_parse_llm_response_gate_enabled_missing_gate_prompt(self):
        """Test that missing gate_prompt raises error when gate is enabled in LLM service."""
        from langhook.subscriptions.llm import LLMPatternService
        
        service = LLMPatternService()
        response = '{"pattern": "langhook.events.github.pull_request.*.created"}'
        
        with pytest.raises(ValueError, match="missing required gate_prompt"):
            service._parse_llm_response(response, gate_enabled=True)

    def test_parse_llm_response_gate_enabled_invalid_json_error(self):
        """Test that invalid JSON raises error when gate is enabled in LLM service."""
        from langhook.subscriptions.llm import LLMPatternService
        
        service = LLMPatternService()
        response = "langhook.events.github.pull_request.*.created"  # Just pattern, no JSON
        
        with pytest.raises(ValueError, match="LLM failed to return properly formatted JSON"):
            service._parse_llm_response(response, gate_enabled=True)

    def test_parse_llm_response_gate_enabled_with_valid_json(self):
        """Test parsing valid JSON response when gate is enabled in LLM service."""
        from langhook.subscriptions.llm import LLMPatternService
        
        service = LLMPatternService()
        response = '{"pattern": "langhook.events.github.pull_request.*.created", "gate_prompt": "Evaluate if this is a GitHub PR"}'
        
        result = service._parse_llm_response(response, gate_enabled=True)
        
        assert result is not None
        assert result["pattern"] == "langhook.events.github.pull_request.*.created"
        assert result["gate_prompt"] == "Evaluate if this is a GitHub PR"


class TestGateConfigSchema:
    """Test gate configuration schema validation."""

    def test_gate_config_defaults(self):
        """Test that gate config has proper defaults."""
        config = GateConfig()
        
        assert config.enabled is False
        assert config.prompt == ""

    def test_gate_config_validation(self):
        """Test gate config validation."""
        # Valid config
        config = GateConfig(
            enabled=True,
            prompt="Test prompt for evaluation"
        )
        
        assert config.enabled is True
        assert config.prompt == "Test prompt for evaluation"


class TestPromptLibrary:
    """Test prompt library functionality (fallback templates)."""

    def test_prompt_library_loads_defaults(self):
        """Test that prompt library loads default fallback templates."""
        library = PromptLibrary()
        
        assert "default" in library.templates
        assert "strict" in library.templates
        assert "precise" in library.templates
        assert "security_focused" in library.templates
        assert "exact_match" in library.templates

    def test_get_template(self):
        """Test getting a template by name."""
        library = PromptLibrary()
        
        default_template = library.get_template("default")
        assert "intelligent event filter" in default_template.lower()
        # Updated to only expect decision in JSON response
        assert "decision" in default_template
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