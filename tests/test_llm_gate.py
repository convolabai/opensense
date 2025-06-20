"""Tests for LLM Gate functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from langhook.subscriptions.gate import LLMGateService
from langhook.subscriptions.prompts import PromptLibrary
from langhook.subscriptions.schemas import GateConfig


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

    def test_parse_llm_response_handles_json_pattern(self):
        """Test that _parse_llm_response correctly extracts pattern from JSON response."""
        from langhook.subscriptions.llm import LLMPatternService

        service = LLMPatternService()
        response = '{"pattern": "langhook.events.github.pull_request.*.created"}'

        result = service._parse_llm_response(response)

        assert result is not None
        assert result["pattern"] == "langhook.events.github.pull_request.*.created"

    def test_parse_llm_response_handles_plain_pattern(self):
        """Test that _parse_llm_response correctly extracts plain pattern response."""
        from langhook.subscriptions.llm import LLMPatternService

        service = LLMPatternService()
        response = "langhook.events.github.pull_request.*.created"

        result = service._parse_llm_response(response)

        assert result is not None
        assert result["pattern"] == "langhook.events.github.pull_request.*.created"

    def test_convert_to_pattern_and_gate_adds_description_as_gate_prompt(self):
        """Test that convert_to_pattern_and_gate uses description as gate_prompt when gate is enabled."""
        from unittest.mock import AsyncMock

        from langhook.subscriptions.llm import LLMPatternService

        # Test the key behavior: when gate_enabled=True, result should include gate_prompt with description
        # We'll mock the entire method chain to focus on this specific functionality

        description = "GitHub pull requests"
        expected_pattern = "langhook.events.github.pull_request.*.created"

        with patch.object(LLMPatternService, '__init__', return_value=None):
            service = LLMPatternService()

            # Mock the internal method calls to simulate successful pattern extraction
            with patch.object(service, '_get_system_prompt_with_schemas', return_value="mock_system_prompt"):
                with patch.object(service, '_create_user_prompt', return_value="mock_user_prompt"):
                    with patch.object(service, '_is_no_schema_response', return_value=False):
                        with patch.object(service, '_parse_llm_response', return_value={"pattern": expected_pattern}):
                            # Mock the LLM service parts
                            service.llm = AsyncMock()
                            service.llm.ainvoke.return_value.content = expected_pattern

                            import asyncio

                            # Test with gate_enabled=False
                            result_no_gate = asyncio.run(service.convert_to_pattern_and_gate(description, gate_enabled=False))
                            assert "pattern" in result_no_gate
                            assert "gate_prompt" not in result_no_gate

                            # Test with gate_enabled=True
                            result_with_gate = asyncio.run(service.convert_to_pattern_and_gate(description, gate_enabled=True))
                            assert "pattern" in result_with_gate
                            assert "gate_prompt" in result_with_gate
                            assert result_with_gate["gate_prompt"] == description


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
